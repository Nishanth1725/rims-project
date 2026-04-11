import uuid
import logging
from flask import session, current_app
from flask_login import current_user
from extensions import db
from models import Cart, CartItem

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _make_session_key():
    """Generate a unique session key for guest cart."""
    return "cart_" + uuid.uuid4().hex


# -------------------------------------------------
# Get or Create Cart
# -------------------------------------------------
def get_or_create_cart():
    """
    Returns a Cart instance.

    Logic:
    - Logged-in user → cart linked to user_id
    - Guest user → cart linked to session_key
    
    This function is used by auth.py for cart merging on login.
    For cart operations, use the get_or_create_cart() from blueprints.cart module.
    """

    try:
        # -----------------------------
        # Logged-in user
        # -----------------------------
        if current_user.is_authenticated:
            user_id = getattr(current_user, 'id', None)
            if not user_id:
                logger.error("current_user.id is None in cart_utils.get_or_create_cart")
                return None
            
            # Check session for stored cart_id first
            stored_cart_id = session.get('last_cart_id')
            stored_user_id = session.get('last_user_id')
            
            if stored_cart_id and stored_user_id == user_id:
                cart = Cart.query.filter_by(cart_id=stored_cart_id, user_id=user_id).first()
                if cart:
                    logger.info(f"cart_utils: Using stored cart {cart.cart_id} for user {user_id}")
                    return cart
            
            # Find existing cart - prefer one with items
            all_carts = Cart.query.filter_by(user_id=user_id).all()
            if all_carts:
                # Use cart with most items, or first one if all empty
                best_cart = None
                max_items = -1
                for c in all_carts:
                    item_count = CartItem.query.filter_by(cart_id=c.cart_id).count()
                    if item_count > max_items:
                        max_items = item_count
                        best_cart = c
                cart = best_cart if best_cart else all_carts[0]
                logger.info(f"cart_utils: Found existing cart {cart.cart_id} with {max_items} items for user {user_id}")
                return cart

            # Create new user cart
            logger.info(f"cart_utils: Creating new cart for user {user_id}")
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
            db.session.refresh(cart)
            
            # Store in session
            if cart.cart_id:
                session['last_cart_id'] = cart.cart_id
                session['last_user_id'] = user_id
                logger.info(f"cart_utils: Created cart {cart.cart_id} for user {user_id}")
            
            return cart

        # -----------------------------
        # Guest user (session-based)
        # -----------------------------
        session_key = session.get("cart_key")

        if session_key:
            cart = Cart.query.filter_by(session_key=session_key).first()
            if cart:
                return cart

        # Create new guest cart
        session_key = _make_session_key()
        session["cart_key"] = session_key

        cart = Cart(session_key=session_key)
        db.session.add(cart)
        db.session.commit()
        return cart

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to get or create cart: {e}")
        return None
