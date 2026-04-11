"""
User Management Blueprint for Admin
Allows admin to view, edit, and manage users
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import User, Order, Cart
from werkzeug.security import generate_password_hash
from sqlalchemy import func

user_management_bp = Blueprint('user_management', __name__, url_prefix='/admin/users')


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


@user_management_bp.route('/')
@login_required
@admin_required
def index():
    """View all users with stats."""
    users = User.query.order_by(User.created_at.desc()).all()
    user_stats = []

    for user in users:
        order_count = Order.query.filter_by(customer_id=user.id).count()
        total_spent = db.session.query(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).filter(Order.customer_id == user.id).scalar() or 0

        user_stats.append({
            'user': user,
            'order_count': order_count,
            'total_spent': float(total_spent)
        })

    return render_template('admin/users/index.html', user_stats=user_stats)


@user_management_bp.route('/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View detailed information about a specific user."""
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(customer_id=user.id).order_by(Order.order_date.desc()).all()
    cart = Cart.query.filter_by(user_id=user.id).first()

    total_orders = len(orders)
    total_spent = sum(float(order.total_amount) for order in orders)

    return render_template(
        'admin/users/view.html',
        user=user,
        orders=orders,
        cart=cart,
        total_orders=total_orders,
        total_spent=total_spent
    )


@user_management_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user information."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role', '').strip()
            password = request.form.get('password', '').strip()

            if username:
                user.username = username
            if email:
                user.email = email
            if role:
                user.role = role
            if password:
                user.password_hash = generate_password_hash(password)

            db.session.commit()
            current_app.logger.info("User updated: %s (ID: %s)", user.username, user.id)
            flash(f"User {user.username} updated successfully!", "success")
            return redirect(url_for('user_management.view_user', user_id=user.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error updating user: %s", e)
            flash(f"Error updating user: {str(e)}", "danger")

    return render_template('admin/users/edit.html', user=user)


@user_management_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account!", "danger")
        return redirect(url_for('user_management.index'))

    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        current_app.logger.info("User deleted: %s (ID: %s)", username, user.id)
        flash(f"User {username} deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting user: %s", e)
        flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for('user_management.index'))


@user_management_bp.route('/<int:user_id>/cart')
@login_required
@admin_required
def view_user_cart(user_id):
    """View a user's cart (admin only)."""
    user = User.query.get_or_404(user_id)
    cart = Cart.query.filter_by(user_id=user.id).first()

    if not cart:
        flash(f"User {user.username} has no active cart.", "info")
        return redirect(url_for('user_management.view_user', user_id=user_id))

    items = getattr(cart, 'items', [])
    total = sum(float(item.unit_price or 0) * (item.quantity or 0) for item in items)

    return render_template(
        'admin/users/cart.html',
        user=user,
        cart=cart,
        items=items,
        total=total
    )
