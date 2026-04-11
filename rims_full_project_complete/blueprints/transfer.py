# blueprints/transfer.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Transfer, Product, Warehouse

transfer_bp = Blueprint('transfer', __name__, url_prefix='/transfer')


@transfer_bp.route('/')
def index():
    """List all transfers."""
    items = Transfer.query.all()
    return render_template('transfer/index.html', items=items)


@transfer_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new product transfer between warehouses."""
    products = Product.query.all()
    warehouses = Warehouse.query.all()

    if request.method == 'POST':
        try:
            pid = request.form.get('product_id')
            quantity = request.form.get('quantity', 1)
            from_w = request.form.get('from_warehouse')
            to_w = request.form.get('to_warehouse')

            # Validate product
            product = Product.query.get(pid)
            if not product:
                flash('Invalid product selected.', 'danger')
                return redirect(url_for('transfer.create'))

            # Validate quantity
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    flash('Quantity must be greater than zero.', 'danger')
                    return redirect(url_for('transfer.create'))
            except (ValueError, TypeError):
                flash('Invalid quantity value.', 'danger')
                return redirect(url_for('transfer.create'))

            # Validate warehouses
            from_warehouse = Warehouse.query.get(from_w) if from_w else None
            to_warehouse = Warehouse.query.get(to_w) if to_w else None
            if not from_warehouse or not to_warehouse:
                flash('Invalid warehouse selection.', 'danger')
                return redirect(url_for('transfer.create'))

            # Create transfer record
            transfer = Transfer(
                product_id=pid,
                transfer_quantity=quantity,
                from_warehouse_id=from_warehouse.id,
                to_warehouse_id=to_warehouse.id
            )
            db.session.add(transfer)
            db.session.commit()

            current_app.logger.info(
                "Transfer created: Product %s, Qty %s from Warehouse %s to Warehouse %s",
                product.product_name, quantity, from_warehouse.name, to_warehouse.name
            )
            flash('Transfer created successfully!', 'success')
            return redirect(url_for('transfer.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating transfer: %s", e)
            flash(f'Error creating transfer: {str(e)}', 'danger')
            return redirect(url_for('transfer.create'))

    return render_template('transfer/create.html', products=products, warehouses=warehouses)
