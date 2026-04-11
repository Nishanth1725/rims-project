# blueprints/provider.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Provider

provider_bp = Blueprint('provider', __name__, url_prefix='/provider')


@provider_bp.route('/')
def index():
    """List all providers."""
    providers = Provider.query.all()
    return render_template('provider/index.html', providers=providers)


@provider_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new provider."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            address = request.form.get('address', '').strip()

            if not name:
                flash('Provider name is required!', 'danger')
                return redirect(url_for('provider.create'))

            if not address:
                flash('Provider address is required!', 'danger')
                return redirect(url_for('provider.create'))

            provider = Provider(provider_name=name, provider_address=address)
            db.session.add(provider)
            db.session.commit()

            current_app.logger.info("Provider created: %s (ID: %s)", name, provider.id)
            flash('Provider created successfully!', 'success')
            return redirect(url_for('provider.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception("Error creating provider: %s", e)
            flash(f'Error creating provider: {str(e)}', 'danger')
            return redirect(url_for('provider.create'))

    return render_template('provider/create.html')
