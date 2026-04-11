from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Product, Inventory, Payment, Order, User, Warehouse, Provider, PaymentNotification, OrderDetail
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# -----------------------
# Admin-only decorator
# -----------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# -----------------------
# Admin Dashboard
# -----------------------
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():

    # Total products
    try:
        total_products = Product.query.count()
    except Exception:
        total_products = 0

    # Low stock products
    try:
        low_stock = Inventory.query.filter(
            Inventory.quantity_available <= 5
        ).count()
    except Exception:
        low_stock = 0

    # Sales in last 30 days (FIXED STATUS)
    now = datetime.utcnow()
    one_month_ago = now - timedelta(days=30)

    try:
        sales_sum = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(
            Order, Payment.order_id == Order.order_id
        ).filter(
            and_(
                Payment.created_at >= one_month_ago,
                or_(
                    Payment.payment_status == 'paid',
                    Payment.status == 'paid'
                ),
                Order.admin_id == current_user.id
            )
        ).scalar() or 0
    except Exception:
        sales_sum = 0

    # Other counts
    try:
        total_orders = Order.query.count()
    except Exception:
        total_orders = 0

    try:
        total_users = User.query.count()
    except Exception:
        total_users = 0

    try:
        warehouses_count = Warehouse.query.count()
    except Exception:
        warehouses_count = 0

    try:
        providers_count = Provider.query.count()
    except Exception:
        providers_count = 0

    # Recent orders
    try:
        recent_orders = Order.query.order_by(
            Order.order_date.desc()
        ).limit(10).all()
    except Exception:
        recent_orders = []

    # Payment notifications - pending verification payments
    try:
        pending_payments = db.session.query(Payment).join(
            Order, Payment.order_id == Order.order_id
        ).filter(
            and_(
                or_(
                    Payment.status == 'pending_verification',
                    Payment.payment_status == 'pending_verification'
                ),
                Order.admin_id == current_user.id
            )
        ).order_by(Payment.payment_timestamp.desc()).all()
        
        # Also get unread payment notifications
        unread_notifications = PaymentNotification.query.filter(
            and_(
                PaymentNotification.retailer_id == current_user.id,
                PaymentNotification.is_read == False
            )
        ).order_by(PaymentNotification.created_at.desc()).all()
    except Exception as e:
        print(f"Error loading payments: {e}")
        pending_payments = []
        unread_notifications = []

    # Today's orders and revenue
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        todays_orders = Order.query.filter(
            and_(
                Order.admin_id == current_user.id,
                Order.order_date >= today_start
            )
        ).count()
        
        todays_revenue = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(
            Order, Payment.order_id == Order.order_id
        ).filter(
            and_(
                Payment.created_at >= today_start,
                or_(
                    Payment.status.in_(['paid', 'received']),
                    Payment.payment_status.in_(['paid', 'received'])
                ),
                Order.admin_id == current_user.id
            )
        ).scalar() or 0
        
        pending_deliveries = Order.query.filter(
            and_(
                Order.admin_id == current_user.id,
                Order.status.in_(['pending', 'confirmed', 'shipped'])
            )
        ).count()
        
        cancelled_orders = Order.query.filter(
            and_(
                Order.admin_id == current_user.id,
                Order.status == 'cancelled'
            )
        ).count()
    except Exception:
        todays_orders = 0
        todays_revenue = 0
        pending_deliveries = 0
        cancelled_orders = 0

    return render_template(
        'admin/dashboard.html',
        total_products=total_products,
        low_stock=low_stock,
        sales_sum=sales_sum,
        total_orders=total_orders,
        total_users=total_users,
        warehouses_count=warehouses_count,
        providers_count=providers_count,
        recent_orders=recent_orders,
        pending_payments=pending_payments,
        unread_notifications=unread_notifications,
        todays_orders=todays_orders,
        todays_revenue=todays_revenue,
        pending_deliveries=pending_deliveries,
        cancelled_orders=cancelled_orders
    )


# -----------------------
# Payment Management Routes
# -----------------------
@admin_bp.route('/payments')
@login_required
@admin_required
def payments():
    """View all payment notifications and pending payments."""
    # Get payments marked as done by user, waiting for retailer confirmation
    try:
        pending_payments = db.session.query(Payment).join(
            Order, Payment.order_id == Order.order_id
        ).filter(
            and_(
                Payment.payment_status == 'payment_done',  # Payments marked as done by user
                Order.admin_id == current_user.id
            )
        ).order_by(Payment.payment_timestamp.desc()).all()
    except Exception as e:
        print(f"Error loading pending payments: {e}")
        pending_payments = []
    
    # Get all payment notifications
    try:
        notifications = PaymentNotification.query.filter(
            PaymentNotification.retailer_id == current_user.id
        ).order_by(PaymentNotification.created_at.desc()).limit(50).all()
    except Exception:
        notifications = []
    
    return render_template(
        'admin/payments.html',
        pending_payments=pending_payments,
        notifications=notifications
    )


@admin_bp.route('/payments/confirm/<int:payment_id>', methods=['POST'])
@login_required
@admin_required
def confirm_payment(payment_id):
    """Confirm a payment marked as done by user."""
    try:
        payment = Payment.query.get_or_404(payment_id)
        order = Order.query.get(payment.order_id)
        
        # Verify this payment belongs to the current retailer
        if not order or order.admin_id != current_user.id:
            flash("Access denied. This payment does not belong to you.", "danger")
            return redirect(url_for('admin.payments'))
        
        # Verify payment is marked as done by user (waiting for retailer confirmation)
        if payment.payment_status != 'payment_done':
            flash("Payment is not in pending confirmation status.", "warning")
            return redirect(url_for('admin.payments'))
        
        # Update payment status
        payment.status = 'paid'
        payment.payment_status = 'paid'
        payment.confirmed_at = datetime.utcnow()
        order.status = 'confirmed'  # Or 'paid' depending on your workflow
        
        # Mark related notifications as read
        notifications = PaymentNotification.query.filter_by(
            payment_id=payment_id,
            retailer_id=current_user.id,
            is_read=False
        ).all()
        for notif in notifications:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f"Payment confirmed successfully for Order #{order.order_id}.", "success")
        return redirect(url_for('admin.payments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error confirming payment: {str(e)}", "danger")
        return redirect(url_for('admin.payments'))


@admin_bp.route('/payments/update-order-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    """Update order status (e.g., Paid, Shipped, Delivered)."""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Verify this order belongs to the current retailer
        if order.admin_id != current_user.id:
            flash("Access denied. This order does not belong to you.", "danger")
            return redirect(url_for('admin.payments'))
        
        new_status = request.form.get('status')
        valid_statuses = ['new', 'confirmed', 'paid', 'shipped', 'delivered', 'cancelled']
        
        if new_status not in valid_statuses:
            flash("Invalid status.", "danger")
            return redirect(url_for('admin.payments'))
        
        order.status = new_status
        db.session.commit()
        
        flash(f"Order #{order.order_id} status updated to {new_status}.", "success")
        return redirect(url_for('admin.payments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating order status: {str(e)}", "danger")
        return redirect(url_for('admin.payments'))


@admin_bp.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
@admin_required
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    try:
        notification = PaymentNotification.query.get_or_404(notification_id)
        
        # Verify this notification belongs to the current retailer
        if notification.retailer_id != current_user.id:
            flash("Access denied.", "danger")
            return redirect(url_for('admin.payments'))
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('admin.payments'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error marking notification as read: {str(e)}", "danger")
        return redirect(url_for('admin.payments'))
