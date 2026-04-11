"""
Reports and Analytics Blueprint for Admin
Provides sales reports, inventory reports, product performance, and user activity
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models import Order, Payment, Product, Inventory, User, OrderDetail
from datetime import datetime, timedelta
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__, url_prefix='/admin/reports')


def admin_required(f):
    """Decorator to require admin role."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('auth.login_admin'))
        return f(*args, **kwargs)
    return decorated_function


@reports_bp.route('/')
@login_required
@admin_required
def index():
    """Reports dashboard."""
    return render_template('admin/reports/index.html')


@reports_bp.route('/sales')
@login_required
@admin_required
def sales_report():
    """Sales report with optional date range filtering."""
    # Parse date range from query params
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.utcnow() - timedelta(days=30)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else datetime.utcnow()
    except Exception:
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

    # Fetch orders and payments
    orders = Order.query.filter(Order.order_date.between(start_date, end_date)).all()
    payments = Payment.query.filter(
        Payment.created_at.between(start_date, end_date),
        Payment.status.in_(['paid', 'completed'])
    ).all()

    total_revenue = sum(float(p.amount) for p in payments)
    total_orders = len(orders)
    total_items_sold = sum(sum(item.order_quantity for item in getattr(order, 'items', [])) for order in orders)

    # Daily sales summary
    daily_sales = db.session.query(
        func.date(Order.order_date).label('date'),
        func.count(Order.order_id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        Order.order_date.between(start_date, end_date)
    ).group_by(func.date(Order.order_date)).all()

    return render_template(
        'admin/reports/sales.html',
        orders=orders,
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_items_sold=total_items_sold,
        daily_sales=daily_sales,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )


@reports_bp.route('/inventory')
@login_required
@admin_required
def inventory_report():
    """Inventory stock levels and movements report."""
    try:
        low_stock = Inventory.query.filter(
            Inventory.reorder_point != None,
            Inventory.quantity_available <= Inventory.reorder_point
        ).all()
        out_of_stock = Inventory.query.filter(Inventory.quantity_available == 0).all()
        all_inventory = Inventory.query.join(Product).all()
        total_value = sum(float(inv.product.unit_price or 0) * inv.quantity_available for inv in all_inventory if inv.product)
    except Exception:
        low_stock = []
        out_of_stock = []
        all_inventory = []
        total_value = 0

    return render_template(
        'admin/reports/inventory.html',
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        all_inventory=all_inventory,
        total_value=total_value
    )


@reports_bp.route('/products')
@login_required
@admin_required
def products_report():
    """Product sales and performance report."""
    try:
        # Top selling products
        top_products = db.session.query(
            Product.product_id,
            Product.product_name,
            func.coalesce(func.sum(OrderDetail.order_quantity), 0).label('total_sold'),
            func.coalesce(func.sum(OrderDetail.order_quantity * OrderDetail.unit_price), 0).label('revenue')
        ).outerjoin(OrderDetail, Product.product_id == OrderDetail.product_id)\
         .group_by(Product.product_id, Product.product_name)\
         .having(func.coalesce(func.sum(OrderDetail.order_quantity), 0) > 0)\
         .order_by(func.coalesce(func.sum(OrderDetail.order_quantity), 0).desc())\
         .limit(10).all()
    except Exception:
        top_products = []

    try:
        # Count products per category
        products_by_category = db.session.query(
            Product.category_id,
            func.count(Product.product_id).label('count')
        ).group_by(Product.category_id).all()
    except Exception:
        products_by_category = []

    return render_template(
        'admin/reports/products.html',
        top_products=top_products,
        products_by_category=products_by_category
    )


@reports_bp.route('/users')
@login_required
@admin_required
def users_report():
    """User activity and statistics report."""
    try:
        total_users = User.query.count()
        admin_count = User.query.filter_by(role='admin').count()
        customer_count = User.query.filter_by(role='customer').count()

        # Top customers by orders and spending
        top_customers = db.session.query(
            User.id,
            User.username,
            User.email,
            func.count(Order.order_id).label('order_count'),
            func.coalesce(func.sum(Order.total_amount), 0).label('total_spent')
        ).join(Order, User.id == Order.customer_id)\
         .group_by(User.id, User.username, User.email)\
         .order_by(func.count(Order.order_id).desc())\
         .limit(10).all()

        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    except Exception:
        total_users = admin_count = customer_count = 0
        top_customers = recent_users = []

    return render_template(
        'admin/reports/users.html',
        total_users=total_users,
        admin_count=admin_count,
        customer_count=customer_count,
        top_customers=top_customers,
        recent_users=recent_users
    )
