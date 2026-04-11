# blueprints/user_dashboard.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import Order, OrderDetail, User
from extensions import db
from werkzeug.security import generate_password_hash

user_bp = Blueprint('user_dashboard', __name__, url_prefix='/user')


@user_bp.route('/orders')
@login_required
def orders():
    """List all orders for the logged-in user."""
    orders = Order.query.filter_by(customer_id=current_user.id)\
                        .order_by(Order.order_date.desc()).all()
    return render_template('user/orders.html', orders=orders)


@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Show details of a specific order."""
    from models import Payment
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for('user_dashboard.orders'))
    payment = Payment.query.filter_by(order_id=order_id).first()
    return render_template('user/order_detail.html', order=order, payment=payment)


@user_bp.route('/profile')
@login_required
def profile():
    """Display user profile."""
    return render_template('user/profile.html', user=current_user)


@user_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile including email and password."""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()

            if email:
                current_user.email = email

            if password:
                current_user.password_hash = generate_password_hash(password)

            db.session.commit()
            current_app.logger.info("User profile updated: %s", current_user.username)
            flash("Profile updated successfully!", "success")
            return redirect(url_for('user_dashboard.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error updating profile: %s", e)
            flash(f"Error updating profile: {str(e)}", "danger")
            return redirect(url_for('user_dashboard.edit_profile'))

    return render_template('user/edit_profile.html', user=current_user)


@user_bp.route('/addresses')
@login_required
def addresses():
    """Display user's saved addresses (can be expanded later)."""
    return render_template('user/addresses.html')


@user_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with recent orders and stats."""
    recent_orders = Order.query.filter_by(customer_id=current_user.id)\
                               .order_by(Order.order_date.desc())\
                               .limit(5).all()
    total_orders = Order.query.filter_by(customer_id=current_user.id).count()
    return render_template(
        'user/dashboard.html',
        orders=recent_orders,
        total_orders=total_orders,
        user=current_user
    )
