import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)

# ============================================================
# USER REGISTER
# ============================================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.register"))

        # uniqueness checks
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register"))

        if email and User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        try:
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role="customer"
            )
            db.session.add(user)
            db.session.commit()

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("auth.login"))

        except IntegrityError:
            db.session.rollback()
            flash("Username or email already exists.", "danger")
        except Exception:
            db.session.rollback()
            logger.exception("User registration failed")
            flash("Unexpected error occurred.", "danger")

    return render_template("auth/register.html", type="user")


# ============================================================
# ADMIN REGISTER
# ============================================================
@auth_bp.route("/register_admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("auth.register_admin"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("auth.register_admin"))

        if email and User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("auth.register_admin"))

        try:
            admin = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

            flash("Admin account created. Please log in.", "success")
            return redirect(url_for("auth.login_admin"))

        except IntegrityError:
            db.session.rollback()
            flash("Username or email already exists.", "danger")
        except Exception:
            db.session.rollback()
            logger.exception("Admin registration failed")
            flash("Unexpected error occurred.", "danger")

    return render_template("auth/register.html", type="admin")


# ============================================================
# USER LOGIN
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password required.", "danger")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user)

        # Merge guest cart safely
        try:
            from blueprints.cart_utils import get_or_create_cart
            get_or_create_cart()
        except Exception:
            logger.exception("Cart merge skipped")

        flash("Logged in successfully.", "success")
        return redirect(url_for("catalog.catalog"))

    return render_template("auth/login.html", type="user")


# ============================================================
# ADMIN LOGIN
# ============================================================
@auth_bp.route("/login_admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password required.", "danger")
            return redirect(url_for("auth.login_admin"))

        user = User.query.filter_by(username=username).first()

        if (
            not user
            or not check_password_hash(user.password_hash, password)
            or user.role != "admin"
        ):
            flash("Invalid admin credentials.", "danger")
            return redirect(url_for("auth.login_admin"))

        login_user(user)

        flash("Admin login successful.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("auth/login.html", type="admin")


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
