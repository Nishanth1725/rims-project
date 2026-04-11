from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Inventory, Product, Warehouse
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


# -----------------------------
# Inventory list
# -----------------------------
@inventory_bp.route('/')
def index():
    items = Inventory.query.order_by(Inventory.updated_at.desc()).all()
    return render_template('inventory/index.html', items=items)


# -----------------------------
# Add inventory
# -----------------------------
@inventory_bp.route('/add', methods=['GET', 'POST'])
def add():
    products = Product.query.all()
    warehouses = Warehouse.query.all()

    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id')
            warehouse_id = request.form.get('warehouse_id')
            qty = request.form.get('quantity', '0')

            # Validate required fields
            if not product_id or not warehouse_id:
                flash('Product and Warehouse are required!', 'danger')
                return redirect(url_for('inventory.add'))

            # Convert to integers
            try:
                product_id = int(product_id)
                warehouse_id = int(warehouse_id)
                qty = int(qty)
                qty = max(qty, 0)
            except (ValueError, TypeError):
                flash('Invalid input values!', 'danger')
                return redirect(url_for('inventory.add'))

            # Check if inventory already exists
            inv = Inventory.query.filter_by(product_id=product_id, warehouse_id=warehouse_id).first()
            if inv:
                inv.quantity_available = (inv.quantity_available or 0) + qty
                inv.updated_at = datetime.utcnow()
                flash('Inventory updated successfully!', 'success')
                current_app.logger.info("Inventory updated: Product %s, Warehouse %s, Qty: %s",
                                        product_id, warehouse_id, inv.quantity_available)
            else:
                inv = Inventory(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity_available=qty,
                    updated_at=datetime.utcnow()
                )
                db.session.add(inv)
                flash('Inventory added successfully!', 'success')
                current_app.logger.info("Inventory added: Product %s, Warehouse %s, Qty: %s",
                                        product_id, warehouse_id, qty)

            db.session.commit()
            return redirect(url_for('inventory.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error saving inventory: {str(e)}', 'danger')
            current_app.logger.exception("Error adding inventory")
            return redirect(url_for('inventory.add'))

    return render_template('inventory/add.html', products=products, warehouses=warehouses)


# -----------------------------
# Adjust inventory quantity
# -----------------------------
@inventory_bp.route('/adjust/<int:inventory_id>', methods=['GET', 'POST'])
def adjust(inventory_id):
    inv = Inventory.query.get_or_404(inventory_id)

    if request.method == 'POST':
        try:
            qty = request.form.get('quantity')
            if qty is None:
                flash('Quantity is required!', 'danger')
                return redirect(url_for('inventory.adjust', inventory_id=inventory_id))

            try:
                qty = int(qty)
                qty = max(qty, 0)
            except (ValueError, TypeError):
                flash('Invalid quantity!', 'danger')
                return redirect(url_for('inventory.adjust', inventory_id=inventory_id))

            inv.quantity_available = qty
            inv.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Inventory updated successfully!', 'success')
            current_app.logger.info("Inventory adjusted: ID %s, New Qty: %s", inventory_id, qty)
            return redirect(url_for('inventory.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating inventory: {str(e)}', 'danger')
            current_app.logger.exception("Error adjusting inventory")
            return redirect(url_for('inventory.adjust', inventory_id=inventory_id))

    return render_template('inventory/adjust.html', inv=inv)


# -----------------------------
# Delete inventory
# -----------------------------
@inventory_bp.route('/delete/<int:inventory_id>', methods=['POST'])
def delete(inventory_id):
    try:
        inv = Inventory.query.get_or_404(inventory_id)
        product_id = inv.product_id
        warehouse_id = inv.warehouse_id
        db.session.delete(inv)
        db.session.commit()
        flash('Inventory deleted successfully!', 'success')
        current_app.logger.info("Inventory deleted: Product %s, Warehouse %s", product_id, warehouse_id)
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting inventory: {str(e)}', 'danger')
        current_app.logger.exception("Error deleting inventory")
    return redirect(url_for('inventory.index'))
