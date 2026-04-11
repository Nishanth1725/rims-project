# blueprints/warehouse.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Warehouse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/warehouse')


@warehouse_bp.route('/')
def index():
    """List all warehouses."""
    warehouses = Warehouse.query.order_by(Warehouse.created_at.desc()).all()
    return render_template('warehouse/index.html', warehouses=warehouses)


@warehouse_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new warehouse."""
    if request.method == 'POST':
        try:
            warehouse_name = request.form.get('warehouse_name', '').strip()
            capacity = request.form.get('capacity')
            is_refrigerated = request.form.get('is_refrigerated') == '1'

            if not warehouse_name:
                flash('Warehouse name is required!', 'danger')
                return redirect(url_for('warehouse.create'))

            capacity_int = None
            if capacity:
                try:
                    capacity_int = int(capacity)
                    if capacity_int < 0:
                        capacity_int = None
                except ValueError:
                    capacity_int = None

            warehouse = Warehouse(
                warehouse_name=warehouse_name,
                is_refrigerated=is_refrigerated,
                capacity=capacity_int,
                created_at=datetime.utcnow()
            )

            db.session.add(warehouse)
            db.session.flush()  # get ID before commit
            logger.info("Creating warehouse: %s (refrigerated=%s, capacity=%s)", warehouse_name, is_refrigerated, capacity_int)
            db.session.commit()
            logger.info("Warehouse committed successfully with ID %s", warehouse.warehouse_id)
            flash(f'Warehouse "{warehouse_name}" created successfully! (ID: {warehouse.warehouse_id})', 'success')
            return redirect(url_for('warehouse.index'))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error creating warehouse: %s", e)
            flash(f'Error creating warehouse: {str(e)}', 'danger')
            return redirect(url_for('warehouse.create'))

    return render_template('warehouse/create.html')


@warehouse_bp.route('/edit/<int:warehouse_id>', methods=['GET', 'POST'])
def edit(warehouse_id):
    """Edit an existing warehouse."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)

    if request.method == 'POST':
        try:
            warehouse_name = request.form.get('warehouse_name', '').strip()
            capacity = request.form.get('capacity')
            is_refrigerated = request.form.get('is_refrigerated') == '1'

            if not warehouse_name:
                flash('Warehouse name is required!', 'danger')
                return redirect(url_for('warehouse.edit', warehouse_id=warehouse_id))

            capacity_int = None
            if capacity:
                try:
                    capacity_int = int(capacity)
                    if capacity_int < 0:
                        capacity_int = None
                except ValueError:
                    capacity_int = None

            warehouse.warehouse_name = warehouse_name
            warehouse.is_refrigerated = is_refrigerated
            warehouse.capacity = capacity_int

            db.session.commit()
            logger.info("Warehouse updated: %s (ID %s)", warehouse_name, warehouse_id)
            flash(f'Warehouse "{warehouse_name}" updated successfully!', 'success')
            return redirect(url_for('warehouse.index'))

        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating warehouse: %s", e)
            flash(f'Error updating warehouse: {str(e)}', 'danger')
            return redirect(url_for('warehouse.edit', warehouse_id=warehouse_id))

    return render_template('warehouse/edit.html', warehouse=warehouse)


@warehouse_bp.route('/delete/<int:warehouse_id>', methods=['POST'])
def delete(warehouse_id):
    """Delete a warehouse."""
    warehouse = Warehouse.query.get_or_404(warehouse_id)
    warehouse_name = warehouse.warehouse_name

    try:
        db.session.delete(warehouse)
        db.session.commit()
        logger.info("Warehouse deleted: %s (ID %s)", warehouse_name, warehouse_id)
        flash(f'Warehouse "{warehouse_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Error deleting warehouse: %s", e)
        flash(f'Error deleting warehouse: {str(e)}', 'danger')

    return redirect(url_for('warehouse.index'))
