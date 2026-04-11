from flask import Blueprint, render_template
from models import Product, Inventory
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError

catalog_bp = Blueprint('catalog', __name__, url_prefix='/catalog')


@catalog_bp.route('/')
def catalog():
    try:
        # Only load valid products
        products = Product.query.filter(
            Product.admin_id.isnot(None)
        ).all()
    except (SQLAlchemyError, ProgrammingError) as e:
        error_msg = str(e)
        # Check if this is a missing column error
        if 'does not exist' in error_msg or 'UndefinedColumn' in error_msg:
            from flask import current_app
            current_app.logger.error("Database columns are missing. Run migration: python migrate_product_fields.py")
            from flask import flash
            flash('Database schema needs migration. Please contact administrator.', 'warning')
        products = []
    except Exception as e:
        from flask import current_app
        current_app.logger.exception("Error loading catalog: %s", e)
        products = []

    return render_template('catalog.html', products=products)


@catalog_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    try:
        product = Product.query.get_or_404(product_id)
    except (SQLAlchemyError, ProgrammingError) as e:
        error_msg = str(e)
        # Check if this is a missing column error
        if 'does not exist' in error_msg or 'UndefinedColumn' in error_msg:
            from flask import current_app, flash
            current_app.logger.error("Database columns are missing. Run migration: python migrate_product_fields.py")
            flash('Database schema needs migration. Please contact administrator.', 'warning')
        return "Product not found", 404
    except Exception as e:
        from flask import current_app
        current_app.logger.exception("Error loading product detail: %s", e)
        return "Product not found", 404

    try:
        inventory_items = Inventory.query.filter_by(
            product_id=product_id
        ).all()
    except SQLAlchemyError:
        inventory_items = []

    total_stock = sum(
        item.quantity_available or 0
        for item in inventory_items
    )

    # Safe stock check
    product_qty = product.quantity or 0
    is_in_stock = total_stock > 0 or product_qty > 0

    return render_template(
        'catalog/product_detail.html',
        product=product,
        inventory_items=inventory_items,
        total_stock=total_stock,
        is_in_stock=is_in_stock
    )
