from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Delivery, DeliveryDetail, Product, Warehouse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

delivery_bp = Blueprint('delivery', __name__, url_prefix='/delivery')


# -----------------------
# List deliveries
# -----------------------
@delivery_bp.route('/')
def index():
    try:
        items = Delivery.query.order_by(
            Delivery.sales_date.desc()
        ).all()
    except SQLAlchemyError:
        items = []

    return render_template('delivery/index.html', items=items)


# -----------------------
# Create delivery
# -----------------------
@delivery_bp.route('/create', methods=['GET', 'POST'])
def create():
    products = Product.query.all()
    warehouses = Warehouse.query.all()

    if request.method == 'POST':
        try:
            product_id = int(request.form.get('product_id'))
            warehouse_id = int(request.form.get('warehouse_id'))
            quantity = int(request.form.get('quantity', 1))

            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            # Create delivery
            delivery = Delivery(
                sales_date=datetime.utcnow(),
                status='pending'
            )
            db.session.add(delivery)
            db.session.flush()  # get delivery_id

            # Create delivery detail
            detail = DeliveryDetail(
                delivery_id=delivery.delivery_id,
                product_id=product_id,
                warehouse_id=warehouse_id,
                delivery_quantity=quantity
            )

            db.session.add(detail)
            db.session.commit()

            flash('Delivery created successfully', 'success')
            return redirect(url_for('delivery.index'))

        except (ValueError, SQLAlchemyError) as e:
            db.session.rollback()
            flash(f'Error creating delivery: {str(e)}', 'danger')

    return render_template(
        'delivery/create.html',
        products=products,
        warehouses=warehouses
    )


# -----------------------
# Update delivery status
# -----------------------
@delivery_bp.route('/<int:delivery_id>/update_status', methods=['POST'])
def update_status(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    new_status = request.form.get('status', 'completed')

    try:
        delivery.status = new_status
        db.session.commit()
        flash(
            f'Delivery #{delivery_id} status updated to {new_status}',
            'success'
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error updating delivery status: {str(e)}', 'danger')

    return redirect(url_for('delivery.index'))
