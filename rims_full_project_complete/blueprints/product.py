# blueprints/product.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, Category
from werkzeug.utils import secure_filename
from sqlalchemy.exc import ProgrammingError
import os

product_bp = Blueprint('product', __name__, url_prefix='/product')

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_QR = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


@product_bp.route('/')
@login_required
def index():
    from flask_login import current_user
    from sqlalchemy.exc import ProgrammingError
    # Check if user is authenticated and is admin/retailer
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Admin access required to view products.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        products = Product.query.all()
    except ProgrammingError as e:
        error_msg = str(e)
        if 'does not exist' in error_msg or 'UndefinedColumn' in error_msg:
            flash('Database schema mismatch detected. Please run the migration script: python migrate_product_fields.py', 'danger')
            current_app.logger.error("Database columns are missing. Run migration script.")
            products = []
        else:
            raise
    except Exception as e:
        current_app.logger.exception("Error loading products: %s", e)
        flash('Error loading products. Please try again.', 'danger')
        products = []
    
    return render_template('product/index.html', products=products)


@product_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    # Check if user is authenticated and is admin/retailer
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Admin access required to create products.', 'danger')
        return redirect(url_for('auth.login'))
    
    categories = Category.query.all()
    
    # If no categories exist, warn user
    if not categories and request.method == 'GET':
        flash('No categories found. Please contact administrator to set up categories.', 'warning')
    
    if request.method == 'POST':
        try:
            # Basic product info
            name = request.form.get('name', '').strip()
            if not name:
                flash('Product name is required!', 'danger')
                return redirect(url_for('product.create'))

            price = request.form.get('price') or 0
            try:
                price = float(price)
                if price < 0: price = 0
            except (ValueError, TypeError):
                price = 0

            qty = request.form.get('quantity') or 0
            try:
                qty = int(qty)
                if qty < 0: qty = 0
            except (ValueError, TypeError):
                qty = 0

            delivery_days = request.form.get('delivery_days') or 3
            try:
                delivery_days = int(delivery_days)
                if delivery_days < 1: delivery_days = 3
                if delivery_days > 30: delivery_days = 30
            except (ValueError, TypeError):
                delivery_days = 3

            desc = request.form.get('description', '').strip()
            
            # Category validation - required field
            cat_id_str = request.form.get('category_id', '').strip()
            if not cat_id_str:
                flash('Category is required!', 'danger')
                return redirect(url_for('product.create'))
            
            try:
                cat_id = int(cat_id_str)
                # Validate category exists
                if not Category.query.get(cat_id):
                    flash('Selected category does not exist!', 'danger')
                    return redirect(url_for('product.create'))
            except (ValueError, TypeError):
                flash('Invalid category selected!', 'danger')
                return redirect(url_for('product.create'))

            # Payment options
            payment_methods = request.form.getlist('payment_methods')  # list ['cod','online']
            cod_enabled = 'cod' in payment_methods
            online_payment_enabled = 'online' in payment_methods

            # QR code upload for online payment (required if online payment is enabled)
            qr_filename = None
            if online_payment_enabled:
                qr_file = request.files.get('qr_code')
                if qr_file and qr_file.filename and allowed_file(qr_file.filename, ALLOWED_QR):
                    qfname = secure_filename(qr_file.filename)
                    qr_folder = os.path.join(current_app.root_path, 'static', 'qr_codes')
                    os.makedirs(qr_folder, exist_ok=True)
                    # Add timestamp to avoid filename collisions
                    import time
                    qfname = f"{int(time.time())}_{qfname}"
                    qr_file.save(os.path.join(qr_folder, qfname))
                    qr_filename = qfname
                else:
                    flash('QR code image is required when Online Payment is enabled. Please upload a PNG, JPG, or JPEG image.', 'warning')
                    return redirect(url_for('product.create'))

            # Image upload
            image = request.files.get('image')
            filename = None
            if image and image.filename and allowed_file(image.filename, ALLOWED_IMAGES):
                fname = secure_filename(image.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                # Add timestamp to avoid filename collisions
                import time
                fname = f"{int(time.time())}_{fname}"
                image.save(os.path.join(upload_folder, fname))
                filename = fname

            p = Product(
                product_name=name,
                unit_price=price,
                quantity=qty,
                product_description=desc,
                image_filename=filename,
                category_id=cat_id,
                admin_id=current_user.id,  # Set the retailer/admin who created this product
                cod_enabled=cod_enabled,
                online_payment_enabled=online_payment_enabled,
                qr_code_filename=qr_filename,
                delivery_days=delivery_days
            )
            db.session.add(p)
            db.session.commit()
            current_app.logger.info("Product created: %s (ID: %s) by admin %s", name, p.product_id, current_user.id)
            flash('Product created successfully!', 'success')
            return redirect(url_for('product.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating product: %s", e)
            error_msg = str(e)
            
            # Check for missing column errors
            if 'does not exist' in error_msg or 'UndefinedColumn' in error_msg:
                flash('Database schema mismatch detected. Please run the migration script: python migrate_product_fields.py', 'danger')
                current_app.logger.error("Database columns are missing. Run migration script to add: online_payment_enabled, cod_enabled, qr_code_filename, delivery_days")
            else:
                flash(f'Error creating product: {error_msg}', 'danger')
            return redirect(url_for('product.create'))

    return render_template('product/create.html', categories=categories)


@product_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit(product_id):
    # Check if user is authenticated and is admin/retailer
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Admin access required to edit products.', 'danger')
        return redirect(url_for('auth.login'))
    
    p = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            if name: p.product_name = name

            price = request.form.get('price')
            if price is not None:
                try:
                    p.unit_price = float(price)
                    if p.unit_price < 0: p.unit_price = 0
                except (ValueError, TypeError): pass

            qty = request.form.get('quantity')
            if qty is not None:
                try:
                    p.quantity = int(qty)
                    if p.quantity < 0: p.quantity = 0
                except (ValueError, TypeError): pass

            delivery_days = request.form.get('delivery_days')
            if delivery_days is not None:
                try:
                    p.delivery_days = int(delivery_days)
                    if p.delivery_days < 1: p.delivery_days = 3
                    if p.delivery_days > 30: p.delivery_days = 30
                except (ValueError, TypeError): pass

            desc = request.form.get('description', '').strip()
            if desc: p.product_description = desc

            cat_id = request.form.get('category_id')
            if cat_id is not None:
                try:
                    p.category_id = int(cat_id) if cat_id else None
                except (ValueError, TypeError): pass

            # Payment options
            payment_methods = request.form.getlist('payment_methods')
            p.cod_enabled = 'cod' in payment_methods
            p.online_payment_enabled = 'online' in payment_methods

            # QR code update (only if online payment is enabled)
            if p.online_payment_enabled:
                qr_file = request.files.get('qr_code')
                if qr_file and qr_file.filename and allowed_file(qr_file.filename, ALLOWED_QR):
                    qfname = secure_filename(qr_file.filename)
                    qr_folder = os.path.join(current_app.root_path, 'static', 'qr_codes')
                    os.makedirs(qr_folder, exist_ok=True)
                    # Add timestamp to avoid filename collisions
                    import time
                    qfname = f"{int(time.time())}_{qfname}"
                    # Delete old QR code if exists
                    if p.qr_code_filename:
                        old_qr_path = os.path.join(qr_folder, p.qr_code_filename)
                        if os.path.exists(old_qr_path):
                            try:
                                os.remove(old_qr_path)
                            except Exception:
                                pass
                    qr_file.save(os.path.join(qr_folder, qfname))
                    p.qr_code_filename = qfname
                elif not p.qr_code_filename:
                    # Online payment enabled but no QR code uploaded and no existing QR code
                    flash('QR code image is required when Online Payment is enabled.', 'warning')
                    return redirect(url_for('product.edit', product_id=product_id))

            # Image update
            image = request.files.get('image')
            if image and image.filename and allowed_file(image.filename, ALLOWED_IMAGES):
                fname = secure_filename(image.filename)
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                # Add timestamp to avoid filename collisions
                import time
                fname = f"{int(time.time())}_{fname}"
                # Delete old image if exists
                if p.image_filename:
                    old_img_path = os.path.join(upload_folder, p.image_filename)
                    if os.path.exists(old_img_path):
                        try:
                            os.remove(old_img_path)
                        except Exception:
                            pass
                image.save(os.path.join(upload_folder, fname))
                p.image_filename = fname

            db.session.commit()
            current_app.logger.info("Product updated: %s (ID: %s)", p.product_name, product_id)
            flash('Product updated successfully!', 'success')
            return redirect(url_for('product.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error updating product: %s", e)
            error_msg = str(e)
            
            # Check for missing column errors
            if 'does not exist' in error_msg or 'UndefinedColumn' in error_msg:
                flash('Database schema mismatch detected. Please run the migration script: python migrate_product_fields.py', 'danger')
                current_app.logger.error("Database columns are missing. Run migration script to add: online_payment_enabled, cod_enabled, qr_code_filename, delivery_days")
            else:
                flash(f'Error updating product: {error_msg}', 'danger')
            return redirect(url_for('product.edit', product_id=product_id))

    return render_template('product/edit.html', p=p, categories=categories)


@product_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
def delete(product_id):
    # Check if user is authenticated and is admin/retailer
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Admin access required to delete products.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        p = Product.query.get_or_404(product_id)
        product_name = p.product_name

        # Check if product is in any orders
        from models import OrderDetail
        order_details = OrderDetail.query.filter_by(product_id=product_id).first()
        if order_details:
            flash('Cannot delete product that has been ordered. Archive it instead.', 'danger')
            return redirect(url_for('product.index'))

        db.session.delete(p)
        db.session.commit()
        current_app.logger.info("Product deleted: %s (ID: %s)", product_name, product_id)
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error deleting product: %s", e)
        flash(f'Error deleting product: {str(e)}', 'danger')

    return redirect(url_for('product.index'))
