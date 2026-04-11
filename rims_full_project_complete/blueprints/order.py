# blueprints/order.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime

from extensions import db
from models import Order, OrderDetail, Product, User, Payment

order_bp = Blueprint('order', __name__, url_prefix='/order')


def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('auth.login_admin'))
        return f(*args, **kwargs)
    return decorated_function


@order_bp.route('/')
@login_required
@admin_required
def index():
    """Display all orders (admin only)."""
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('order/index.html', orders=orders)


@order_bp.route('/<int:order_id>')
@login_required
def view(order_id):
    """Display details for a single order."""
    order = Order.query.get_or_404(order_id)

    # Access control: Admin sees all, users see only their own orders
    if current_user.role != 'admin' and order.customer_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('user_dashboard.orders'))

    customer = User.query.get(order.customer_id) if order.customer_id else None
    payment = Payment.query.filter_by(order_id=order.order_id).first()
    return render_template('order/view.html', order=order, customer=customer, payment=payment)


@order_bp.route('/<int:order_id>/update_status', methods=['POST'])
@login_required
@admin_required
def update_status(order_id):
    """Update the status of an order (admin only)."""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')

    valid_statuses = ['new', 'pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if new_status in valid_statuses:
        order.status = new_status
        db.session.commit()
        flash(f"Order status updated to {new_status}.", "success")
    else:
        flash("Invalid status.", "danger")

    return redirect(url_for('order.view', order_id=order_id))


@order_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Create a new order manually (admin only)."""
    products = Product.query.all()

    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        payment_method = request.form.get('payment_method')  # 'cod' or 'online'
        qr_code = request.form.get('qr_code', None)  # Optional QR code URL

        order = Order(
            customer_id=int(customer_id) if customer_id else None,
            order_date=datetime.utcnow(),
            status='pending' if payment_method == 'cod' else 'paid'
        )
        db.session.add(order)
        db.session.flush()  # Get order_id

        pid = request.form.get('product_id')
        qty = int(request.form.get('quantity', 1))
        product = Product.query.get(pid)

        if product:
            # Create order detail
            order_detail = OrderDetail(
                order_id=order.order_id,
                product_id=pid,
                product_name=product.product_name,
                order_quantity=qty,
                unit_price=product.unit_price
            )
            db.session.add(order_detail)

            # Create payment record
            payment = Payment(
                order_id=order.order_id,
                amount=qty * product.unit_price,
                method='Cash on Delivery' if payment_method == 'cod' else 'Online QR',
                status='pending' if payment_method == 'cod' else 'completed',
                qr_code=qr_code,
                created_at=datetime.utcnow()
            )
            db.session.add(payment)

            db.session.commit()

            # Notify admin(s) if customer placed the order (for future enhancement)
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                # Here you can integrate email, SMS, or in-app notification
                print(f"Admin {admin.username} notified for order {order.order_id}")

            flash('Order created successfully.', 'success')
            return redirect(url_for('order.index'))
        else:
            flash('Invalid product selected.', 'danger')

    return render_template('order/create.html', products=products)
