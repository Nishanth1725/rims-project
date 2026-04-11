from flask import (
    Blueprint, render_template, request,
    redirect, url_for, current_app,
    jsonify, flash, session
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from extensions import db
from models import Product, CartItem, Cart
import logging

logger = logging.getLogger(__name__)

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

# -------------------------------------------------
# Cart helper
# -------------------------------------------------
def get_or_create_cart():
    """
    Get or create cart for logged-in user. Returns cart with valid cart_id.
    This function is used by add/update/remove routes, but the main cart route
    has its own implementation for better error handling.
    """
    if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
        logger.warning("get_or_create_cart called but user is not authenticated")
        return None

    try:
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            logger.error("current_user.id is None or invalid")
            return None
        
        logger.info(f"🔍 get_or_create_cart: Looking for cart for user_id={user_id}")
            
        # Try to get existing cart - use explicit query with expire to avoid stale cache
        try:
            db.session.expire_all()  # Clear any cached objects
            all_carts = Cart.query.filter_by(user_id=user_id).all()
            
            if all_carts:
                logger.info(f"🔍 get_or_create_cart: Found {len(all_carts)} cart(s) for user {user_id}")
                
                # If multiple carts exist, use the one with the most items (most likely to be the active one)
                # Also check session for the last used cart_id
                stored_cart_id = session.get('last_cart_id')
                stored_user_id = session.get('last_user_id')
                
                best_cart = None
                max_items = -1
                
                for c in all_carts:
                    item_count = CartItem.query.filter_by(cart_id=c.cart_id).count()
                    logger.info(f"🔍 get_or_create_cart: Cart {c.cart_id} has {item_count} items")
                    
                    # Prioritize the stored cart_id if it matches
                    if stored_cart_id and stored_user_id == user_id and c.cart_id == stored_cart_id:
                        logger.info(f"🔍 get_or_create_cart: Found stored cart_id {stored_cart_id} in database, prioritizing it")
                        best_cart = c
                        max_items = item_count
                        break
                    elif item_count > max_items:
                        max_items = item_count
                        best_cart = c
                
                cart = best_cart if best_cart else all_carts[0]  # Fallback to first cart if all are empty
                logger.info(f"🔍 get_or_create_cart: Selected cart {cart.cart_id} with {max_items} items for user {user_id}")
            else:
                cart = None
                logger.info(f"🔍 get_or_create_cart: No existing cart found for user {user_id}")
        except Exception as query_error:
            logger.exception(f"Database query error in get_or_create_cart for user {user_id}: {query_error}")
            db.session.rollback()
            return None
            
        if cart:
            if hasattr(cart, 'cart_id') and cart.cart_id:
                logger.info(f"✓ get_or_create_cart: Returning existing cart {cart.cart_id} for user {user_id}")
                return cart
            else:
                logger.warning(f"Cart found but cart_id is None for user {user_id}, will create new one")
                # Cart exists but has no ID (shouldn't happen), delete and recreate
                try:
                    db.session.delete(cart)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        
        # Cart doesn't exist, create it
        logger.info(f"Creating new cart for user {user_id}")
        try:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()
            db.session.refresh(cart)
            
            # Verify cart_id was set
            if hasattr(cart, 'cart_id') and cart.cart_id:
                logger.info(f"Successfully created cart {cart.cart_id} for user {user_id}")
                return cart
            else:
                # Query again to get the cart with ID
                new_cart = Cart.query.filter_by(user_id=user_id).first()
                if new_cart and hasattr(new_cart, 'cart_id') and new_cart.cart_id:
                    logger.info(f"Found cart {new_cart.cart_id} after creation for user {user_id}")
                    return new_cart
                else:
                    logger.error(f"Cart created but cart_id is still None for user {user_id}")
                    db.session.rollback()
                    return None
                
        except Exception as commit_error:
            logger.exception(f"Error committing cart creation for user {user_id}: {commit_error}")
            db.session.rollback()
            # Try one more time to get existing cart
            try:
                cart = Cart.query.filter_by(user_id=user_id).first()
                if cart and hasattr(cart, 'cart_id') and cart.cart_id:
                    logger.info(f"Found cart {cart.cart_id} after rollback for user {user_id}")
                    return cart
            except Exception:
                pass
            return None
            
    except Exception as e:
        logger.exception(f"Unexpected error in get_or_create_cart for user {getattr(current_user, 'id', 'unknown')}: {e}")
        try:
            db.session.rollback()
            # Last attempt to get existing cart
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                try:
                    cart = Cart.query.filter_by(user_id=current_user.id).first()
                    if cart and hasattr(cart, 'cart_id') and cart.cart_id:
                        logger.info(f"Recovered cart {cart.cart_id} after error for user {current_user.id}")
                        return cart
                except Exception:
                    pass
        except Exception:
            pass
        return None


# -------------------------------------------------
# View Cart
# -------------------------------------------------
@cart_bp.route('/')
@login_required
def index():
    """Display user's cart with all items."""
    # Initialize default values to prevent template errors
    valid_items = []
    cart_total = 0.0
    cart = None
    
    try:
        # Ensure user is authenticated (should be handled by @login_required, but double-check)
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            logger.warning("Unauthenticated user tried to access cart")
            flash("Please log in to view your cart.", "warning")
            return redirect(url_for('auth.login'))
        
        # Safely get user_id
        try:
            user_id = getattr(current_user, 'id', None)
            if not user_id:
                logger.error("current_user.id is None or invalid")
                flash("Error: Invalid user session. Please log in again.", "danger")
                return redirect(url_for('auth.login'))
        except (AttributeError, TypeError) as e:
            logger.exception(f"Error accessing current_user.id: {e}")
            flash("Error: Invalid user session. Please log in again.", "danger")
            return redirect(url_for('auth.login'))
        
        logger.info(f"=== CART PAGE LOAD: Starting cart load for user {user_id} ===")
        
        # CRITICAL: Check if we have a stored cart_id from the last add operation
        stored_cart_id = session.get('last_cart_id')
        stored_user_id = session.get('last_user_id')
        if stored_cart_id and stored_user_id == user_id:
            logger.info(f"🔍 Found stored cart_id={stored_cart_id} in session for user {user_id}, verifying it exists")
            stored_cart = Cart.query.filter_by(cart_id=stored_cart_id, user_id=user_id).first()
            if stored_cart:
                logger.info(f"✓ Verified stored cart {stored_cart_id} exists and belongs to user {user_id}, using it")
                cart = stored_cart
            else:
                logger.warning(f"⚠ Stored cart_id={stored_cart_id} not found in database, will use get_or_create_cart")
                cart = None
        else:
            cart = None
        
        # CRITICAL DEBUG: Check what carts exist for this user BEFORE calling get_or_create_cart
        try:
            all_user_carts = Cart.query.filter_by(user_id=user_id).all()
            logger.info(f"🔍 DEBUG: Found {len(all_user_carts)} cart(s) for user {user_id}: {[(c.cart_id, c.user_id) for c in all_user_carts]}")
            
            # Check items in ALL carts for this user
            for c in all_user_carts:
                items_in_cart = CartItem.query.filter_by(cart_id=c.cart_id).all()
                logger.info(f"🔍 DEBUG: Cart {c.cart_id} (user_id={c.user_id}) has {len(items_in_cart)} items: {[(i.cart_item_id, i.product_id, i.quantity) for i in items_in_cart]}")
        except Exception as debug_error:
            logger.warning(f"Error in debug check: {debug_error}")
        
        # Get or create cart - USE SAME FUNCTION AS add_to_cart() FOR CONSISTENCY
        try:
            if not cart:
                cart = get_or_create_cart()
            if not cart:
                logger.error(f"✗ get_or_create_cart() returned None for user {user_id}")
                return render_template(
                    'cart/cart.html',
                    items=[],
                    total=0.0,
                    cart=None
                )
            
            if not hasattr(cart, 'cart_id') or not cart.cart_id:
                logger.error(f"✗ Cart has no cart_id for user {user_id}")
                return render_template(
                    'cart/cart.html',
                    items=[],
                    total=0.0,
                    cart=None
                )
            
            # Store the cart_id in session for future consistency
            session['last_cart_id'] = cart.cart_id
            session['last_user_id'] = user_id
            
            logger.info(f"✓ Using cart_id={cart.cart_id} for user {user_id} (same function as add_to_cart)")
            
            # CRITICAL: Expire all cached objects to ensure we see latest committed data
            db.session.expire_all()
            
            # VERIFICATION: Check how many items are in this cart in the database
            try:
                db_items_count = db.session.query(CartItem).filter_by(cart_id=cart.cart_id).count()
                logger.info(f"✓ VERIFICATION: Cart {cart.cart_id} has {db_items_count} item(s) in database for user {user_id}")
                
                # Also verify with direct SQL
                try:
                    direct_count = db.session.execute(
                        text("SELECT COUNT(*) FROM cart_item WHERE cart_id = :cart_id"),
                        {"cart_id": cart.cart_id}
                    ).scalar()
                    logger.info(f"✓ Direct SQL count for cart {cart.cart_id}: {direct_count}")
                    if direct_count != db_items_count:
                        logger.warning(f"⚠ Count mismatch: ORM={db_items_count}, SQL={direct_count} - using SQL count")
                        db_items_count = direct_count
                except Exception as sql_error:
                    logger.warning(f"Could not execute direct SQL count: {sql_error}")
            except Exception as count_error:
                logger.warning(f"Could not count items in cart {cart.cart_id}: {count_error}")
                
        except Exception as e:
            logger.exception(f"✗ Error getting/creating cart for user {user_id}: {e}")
            db.session.rollback()
            # Return empty cart state instead of error
            logger.warning(f"Could not load cart for user {user_id}, showing empty cart")
            return render_template(
                'cart/cart.html',
                items=[],
                total=0.0,
                cart=None
            )
        
        # Verify cart and cart_id before querying items
        if not cart:
            logger.warning(f"Cart is None for user {user_id}, showing empty cart")
            return render_template(
                'cart/cart.html',
                items=[],
                total=0.0,
                cart=None
            )
        
        if not hasattr(cart, 'cart_id') or not cart.cart_id:
            logger.warning(f"Cart cart_id is None for user {user_id}, showing empty cart")
            return render_template(
                'cart/cart.html',
                items=[],
                total=0.0,
                cart=cart
            )
        
        # SIMPLIFIED: Direct query - get items for this cart
        items = []
        try:
            logger.info(f"=== QUERYING CART ITEMS: cart_id={cart.cart_id}, user_id={user_id} ===")
            
            # Expire all cached objects
            db.session.expire_all()
            
            # VERIFY: Double-check cart ownership before querying
            cart_check = Cart.query.filter_by(cart_id=cart.cart_id, user_id=user_id).first()
            if not cart_check:
                logger.error(f"✗ CRITICAL: Cart {cart.cart_id} does not belong to user {user_id} - ownership mismatch!")
                # Try to find the correct cart for this user
                correct_cart = Cart.query.filter_by(user_id=user_id).first()
                if correct_cart:
                    logger.info(f"✓ Found correct cart {correct_cart.cart_id} for user {user_id}, using that instead")
                    cart = correct_cart
                else:
                    logger.error(f"✗ No cart found for user {user_id}")
                    return render_template(
                        'cart/cart.html',
                        items=[],
                        total=0.0,
                        cart=None
                    )
            
            # SIMPLE DIRECT QUERY - no complex joins first
            items = db.session.query(CartItem).filter_by(cart_id=cart.cart_id).all()
            logger.info(f"✓ Direct query returned {len(items)} cart item(s) for cart {cart.cart_id}")
            
            # CRITICAL FIX: If no items found, check ALL carts for this user
            # This handles the case where items were added to a different cart
            if len(items) == 0:
                logger.warning(f"⚠ No items found for cart_id={cart.cart_id}, checking ALL carts for user {user_id}")
                # Query all carts for this user and get all items
                all_user_carts = Cart.query.filter_by(user_id=user_id).all()
                logger.info(f"🔍 Found {len(all_user_carts)} total cart(s) for user {user_id}")
                
                for user_cart in all_user_carts:
                    alt_items = CartItem.query.filter_by(cart_id=user_cart.cart_id).all()
                    logger.info(f"🔍 Cart {user_cart.cart_id} has {len(alt_items)} items")
                    if alt_items:
                        logger.info(f"✓ FOUND {len(alt_items)} items in cart {user_cart.cart_id} - using this cart instead!")
                        items = alt_items
                        cart = user_cart  # Use this cart instead
                        # Update the cart_id for consistency
                        logger.info(f"✓ Switched to cart {cart.cart_id} with {len(items)} items for user {user_id}")
                        break
                
                # If still no items, log all carts and items for debugging
                if len(items) == 0:
                    logger.error(f"✗ CRITICAL: No items found in ANY cart for user {user_id}")
                    logger.error(f"✗ All carts for user {user_id}: {[(c.cart_id, c.user_id) for c in all_user_carts]}")
                    # Check all cart items in database
                    all_items = CartItem.query.all()
                    logger.error(f"✗ All cart items in database: {[(i.cart_item_id, i.cart_id, i.product_id, i.quantity) for i in all_items]}")
            
            # Now load products for each item
            for item in items:
                if not hasattr(item, 'product') or item.product is None:
                    try:
                        product = Product.query.get(item.product_id)
                        if product:
                            item.product = product
                            logger.info(f"✓ Loaded product {item.product_id} ({product.product_name}) for cart item {item.cart_item_id}")
                        else:
                            logger.warning(f"Product {item.product_id} not found for cart item {item.cart_item_id}")
                    except Exception as load_error:
                        logger.warning(f"Error loading product {item.product_id}: {load_error}")
                
        except Exception as e:
            logger.exception(f"✗ Error querying cart items for cart {cart.cart_id}: {e}")
            db.session.rollback()
            items = []  # Set empty list on error - don't fail the page
        
        # SIMPLIFIED: Process items - show ALL items, don't filter aggressively
        valid_items = []
        total = 0.0
        
        logger.info(f"=== PROCESSING {len(items)} ITEMS FOR DISPLAY ===")
        
        # Create minimal product class for missing products
        class MinimalProduct:
            def __init__(self, product_id):
                self.product_id = product_id
                self.product_name = f"Product #{product_id} (Not Available)"
                self.image_filename = None
                self.quantity = 0
        
        try:
            for item in items:
                try:
                    cart_item_id = getattr(item, 'cart_item_id', 'unknown')
                    product_id = getattr(item, 'product_id', None)
                    
                    # Skip if no product_id
                    if not product_id:
                        logger.warning(f"Skipping cart item {cart_item_id} - no product_id")
                        continue
                    
                    # Ensure product is loaded
                    if not hasattr(item, 'product') or item.product is None:
                        product = Product.query.get(product_id)
                        if product:
                            item.product = product
                        else:
                            # Use minimal product if not found
                            item.product = MinimalProduct(product_id)
                            logger.warning(f"Product {product_id} not found, using minimal product")
                    
                    # Get quantity and price
                    quantity = int(getattr(item, 'quantity', 0) or 0)
                    price = float(getattr(item, 'unit_price', 0) or 0)
                    
                    # Only skip if quantity is 0 or negative
                    if quantity <= 0:
                        logger.warning(f"Skipping cart item {cart_item_id} - invalid quantity: {quantity}")
                        continue
                    
                    # Add to valid items
                    item_total = quantity * price
                    total += item_total
                    valid_items.append(item)
                    
                    product_name = getattr(item.product, 'product_name', f'Product #{product_id}')
                    logger.info(f"✓ ADDED: cart_item_id={cart_item_id}, product='{product_name}', quantity={quantity}, price={price}, subtotal={item_total}")
                    
                except Exception as item_error:
                    logger.exception(f"Error processing cart item {getattr(item, 'cart_item_id', 'unknown')}: {item_error}")
                    # Still try to add it if it has basic info
                    try:
                        if hasattr(item, 'product_id') and hasattr(item, 'quantity') and int(getattr(item, 'quantity', 0) or 0) > 0:
                            if not hasattr(item, 'product') or item.product is None:
                                item.product = MinimalProduct(getattr(item, 'product_id'))
                            valid_items.append(item)
                            logger.info(f"✓ ADDED item despite error: cart_item_id={getattr(item, 'cart_item_id', 'unknown')}")
                    except:
                        pass  # Skip this item
                    
        except Exception as e:
            logger.exception(f"Error processing cart items: {e}")
        
        logger.info(f"=== FINAL RESULT: {len(valid_items)} items will be displayed, total=₹{total:.2f} ===")
        
        # Ensure total is a valid number
        try:
            cart_total = float(total) if total else 0.0
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting total to float: {total}, error: {e}")
            cart_total = 0.0
        
        # Ensure valid_items is always a list
        if not isinstance(valid_items, list):
            valid_items = []
        
        # Ensure cart_total is always a number
        if not isinstance(cart_total, (int, float)):
            cart_total = 0.0
        
        user_id_str = getattr(current_user, 'id', 'unknown')
        logger.info(f"=== CART PAGE LOAD COMPLETE: user={user_id_str}, cart_id={getattr(cart, 'cart_id', 'N/A')}, valid_items={len(valid_items)}, total=₹{cart_total:.2f} ===")
        
        # Always render template with valid values
        return render_template(
            'cart/cart.html',
            items=valid_items,  # Always a list (empty or with items)
            total=cart_total,   # Always a float
            cart=cart           # May be None, but template handles it
        )
        
    except Exception as e:
        logger.exception(f"Unexpected error loading cart for user {getattr(current_user, 'id', 'unknown')}: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        
        # Return empty cart state instead of redirecting (better UX)
        try:
            return render_template(
                'cart/cart.html',
                items=[],      # Empty list
                total=0.0,     # Zero total
                cart=None      # No cart object
            )
        except Exception as template_error:
            logger.exception(f"Error rendering cart template: {template_error}")
            flash("Error loading cart. Please try again or contact support.", "danger")
            return redirect(url_for('catalog.catalog'))


# -------------------------------------------------
# Add to Cart
# -------------------------------------------------
@cart_bp.route('/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        # Get product_id and quantity from form or JSON
        product_id = request.form.get('product_id')
        if not product_id and request.is_json:
            product_id = request.json.get('product_id') if request.json else None
        
        quantity = request.form.get('quantity', 1)
        if not quantity and request.is_json:
            quantity = request.json.get('quantity', 1) if request.json else 1

        # Validate product_id
        if not product_id:
            logger.warning(f"Missing product_id in add to cart request from user {current_user.id}")
            return _respond_error("Product ID is required", request.is_json, 400)

        try:
            product_id = int(product_id)
            quantity = max(int(quantity), 1)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid product_id or quantity: product_id={product_id}, quantity={quantity}, error={e}")
            return _respond_error("Invalid product data. Please enter valid product ID and quantity.", request.is_json, 400)

        # Get product - handle 404 gracefully
        try:
            product = Product.query.get(product_id)
            if not product:
                logger.warning(f"Product {product_id} not found when user {current_user.id} tried to add to cart")
                return _respond_error(f"Product not found (ID: {product_id})", request.is_json, 404)
        except Exception as e:
            logger.exception(f"Error querying product {product_id}: {e}")
            db.session.rollback()
            return _respond_error("Error loading product. Please try again.", request.is_json, 500)

        # Get or create cart
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            logger.error("current_user.id is None in add_to_cart")
            return _respond_error("User session invalid. Please log in again.", request.is_json, 401)
        
        logger.info(f"=== ADD TO CART: user_id={user_id}, product_id={product_id}, quantity={quantity} ===")
        
        # CRITICAL DEBUG: Check what carts exist for this user BEFORE calling get_or_create_cart
        try:
            all_user_carts = Cart.query.filter_by(user_id=user_id).all()
            logger.info(f"🔍 DEBUG (ADD): Found {len(all_user_carts)} cart(s) for user {user_id}: {[(c.cart_id, c.user_id) for c in all_user_carts]}")
        except Exception as debug_error:
            logger.warning(f"Error in debug check (ADD): {debug_error}")
        
        cart = get_or_create_cart()
        if not cart:
            logger.error(f"✗ Failed to get or create cart for user {user_id}")
            db.session.rollback()
            return _respond_error("Cart not available. Please try again.", request.is_json, 500)
        
        # Verify cart_id is set (get_or_create_cart should have already committed)
        if not cart.cart_id:
            logger.error(f"✗ Cart ID is None in add_to_cart for user {user_id} - this should not happen")
            return _respond_error("Cart not available. Please try again.", request.is_json, 500)
        
        # Verify cart belongs to this user
        if cart.user_id != user_id:
            logger.error(f"✗ CRITICAL: Cart {cart.cart_id} belongs to user {cart.user_id}, but current user is {user_id} - MISMATCH!")
            return _respond_error("Cart ownership mismatch. Please try again.", request.is_json, 500)
        
        logger.info(f"✓ Using cart_id={cart.cart_id} for user {user_id} (verified ownership)")

        # Check if item already exists in cart
        logger.info(f"Checking for existing cart item: cart_id={cart.cart_id}, product_id={product_id}")
        existing_item = CartItem.query.filter_by(
            cart_id=cart.cart_id,
            product_id=product_id
        ).first()
        
        if existing_item:
            logger.info(f"✓ Found existing cart item: cart_item_id={existing_item.cart_item_id}, current_quantity={existing_item.quantity}")
        else:
            logger.info(f"✓ No existing cart item found, will create new one")

        # Stock validation - account for existing quantity in cart
        if product.quantity is not None:
            current_cart_quantity = existing_item.quantity if existing_item else 0
            total_requested = current_cart_quantity + quantity
            
            if total_requested > product.quantity:
                available = product.quantity - current_cart_quantity
                if available <= 0:
                    message = f"Product '{product.product_name}' is already in your cart with maximum available quantity ({current_cart_quantity})."
                else:
                    message = f"Insufficient stock for '{product.product_name}'. Available: {available}, Requested: {quantity}."
                logger.info(f"Stock check failed for product {product_id}: available={product.quantity}, requested={total_requested}")
                return _respond_error(message, request.is_json, 400)

        # Get unit price
        try:
            unit_price = float(product.unit_price or 0)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid unit_price for product {product_id}: {product.unit_price}, error={e}")
            unit_price = 0

        # Update or create cart item
        if existing_item:
            old_quantity = existing_item.quantity
            existing_item.quantity += quantity
            # Update unit_price if it changed (in case product price was updated)
            if existing_item.unit_price != unit_price:
                existing_item.unit_price = unit_price
            logger.info(f"✓ Updating existing cart item {existing_item.cart_item_id}: quantity {old_quantity} → {existing_item.quantity} for user {current_user.id}")
        else:
            existing_item = CartItem(
                cart_id=cart.cart_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price
            )
            db.session.add(existing_item)
            logger.info(f"✓ Creating new cart item: cart_id={cart.cart_id}, product_id={product_id}, quantity={quantity}, unit_price={unit_price} for user {current_user.id}")

        # Commit changes
        try:
            # Flush before commit to ensure data is in the session
            db.session.flush()
            db.session.commit()
            
            # CRITICAL VERIFICATION: Only return success if item is actually saved
            verification_passed = False
            try:
                # Expire all objects to force fresh query from database
                db.session.expire_all()
                
                # Use a fresh query to verify cart item exists in database
                verification_item = db.session.query(CartItem).filter_by(
                    cart_id=cart.cart_id,
                    product_id=product_id
                ).first()
                
                if verification_item:
                    logger.info(f"✓ VERIFIED: Cart item saved successfully - cart_id={cart.cart_id}, cart_item_id={verification_item.cart_item_id}, product_id={product_id}, quantity={verification_item.quantity}, user_id={current_user.id}")
                    verification_passed = True
                else:
                    logger.error(f"✗ VERIFICATION FAILED: Cart item NOT found in database after commit - cart_id={cart.cart_id}, product_id={product_id}, user_id={current_user.id}")
                    # Try one more time with a direct query
                    try:
                        direct_item = db.session.execute(
                            text("SELECT cart_item_id, cart_id, product_id, quantity FROM cart_item WHERE cart_id = :cart_id AND product_id = :product_id"),
                            {"cart_id": cart.cart_id, "product_id": product_id}
                        ).first()
                        if direct_item:
                            logger.info(f"✓ Found item using direct SQL query: cart_item_id={direct_item[0]}, quantity={direct_item[3]}")
                            verification_passed = True
                        else:
                            logger.error(f"✗ Item still not found even with direct SQL query - COMMIT MAY HAVE FAILED SILENTLY")
                    except Exception as sql_error:
                        logger.exception(f"Error executing direct SQL verification: {sql_error}")
                    
                # Also verify cart exists
                verification_cart = db.session.query(Cart).filter_by(user_id=current_user.id, cart_id=cart.cart_id).first()
                if verification_cart:
                    all_items_count = db.session.query(CartItem).filter_by(cart_id=cart.cart_id).count()
                    logger.info(f"✓ VERIFIED: Cart exists with {all_items_count} total item(s) - cart_id={cart.cart_id}, user_id={current_user.id}")
                else:
                    logger.error(f"✗ VERIFICATION FAILED: Cart NOT found in database after commit - cart_id={cart.cart_id}, user_id={current_user.id}")
                    verification_passed = False
                    
            except Exception as verify_error:
                logger.exception(f"Error during verification after commit: {verify_error}")
                verification_passed = False
            
            # ONLY return success if verification passed
            if not verification_passed:
                logger.error(f"✗ CRITICAL: Verification failed for user {current_user.id}, product {product_id} - NOT returning success")
                db.session.rollback()
                return _respond_error("Item was not saved to cart. Please try again.", request.is_json, 500)
            
            # Verification passed - return success
            # CRITICAL: Store cart_id in session to ensure consistency
            session['last_cart_id'] = cart.cart_id
            session['last_user_id'] = user_id
            logger.info(f"✓ Stored cart_id={cart.cart_id} and user_id={user_id} in session for consistency")
            
            if request.is_json:
                return jsonify(success=True, message=f"Added {quantity} x {product.product_name} to cart", cart_id=cart.cart_id)
            
            flash(f"Added {quantity} x {product.product_name} to cart", "success")
            # Redirect based on referrer or default to cart
            referrer = request.referrer
            if referrer and 'catalog' in referrer:
                return redirect(referrer)
            return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception(f"Error committing cart item for user {current_user.id}, product {product_id}: {e}")
            db.session.rollback()
            return _respond_error("Error saving to cart. Please try again.", request.is_json, 500)

    except Exception as e:
        logger.exception(f"Unexpected error in add_to_cart for user {current_user.id}: {e}")
        db.session.rollback()
        return _respond_error("Server error while adding to cart. Please try again.", request.is_json, 500)


# -------------------------------------------------
# Remove Cart Item
# -------------------------------------------------
@cart_bp.route('/remove/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_item(cart_item_id):
    try:
        cart = get_or_create_cart()
        if not cart:
            logger.error(f"Cart not found for user {current_user.id} when trying to remove item {cart_item_id}")
            return _respond_error("Cart not found", request.is_json, 404)
        
        # Verify cart_id is set (get_or_create_cart should have already committed)
        if not cart.cart_id:
            logger.error(f"Cart ID is None in remove_item for user {current_user.id}")
            return _respond_error("Cart not available. Please try again.", request.is_json, 500)
        
        item = CartItem.query.filter_by(
            cart_item_id=cart_item_id,
            cart_id=cart.cart_id
        ).first()

        if not item:
            logger.warning(f"Cart item {cart_item_id} not found in cart {cart.cart_id} for user {current_user.id}")
            if request.is_json:
                return jsonify(success=False, message="Item not found in cart"), 404
            flash("Item not found in cart", "warning")
            return redirect(url_for('cart.index'))

        # Get product name for flash message
        product_name = item.product.product_name if item.product else "Item"
        
        db.session.delete(item)
        db.session.commit()

        logger.info(f"Removed cart item {cart_item_id} from cart {cart.cart_id} for user {current_user.id}")

        if request.is_json:
            return jsonify(success=True, message=f"{product_name} removed from cart")

        flash(f"{product_name} removed from cart", "success")
        return redirect(url_for('cart.index'))

    except Exception as e:
        logger.exception(f"Error removing cart item {cart_item_id} for user {current_user.id}: {e}")
        db.session.rollback()
        return _respond_error("Error removing item. Please try again.", request.is_json, 500)


# -------------------------------------------------
# Update Cart Item
# -------------------------------------------------
@cart_bp.route('/update/<int:cart_item_id>', methods=['POST'])
@login_required
def update_item(cart_item_id):
    try:
        quantity = request.form.get('quantity')
        if not quantity and request.is_json:
            quantity = request.json.get('quantity') if request.json else None

        if not quantity:
            return _respond_error("Quantity is required", request.is_json, 400)

        try:
            quantity = max(int(quantity), 1)
        except (TypeError, ValueError) as e:
            logger.warning(f"Invalid quantity value: {quantity}, error={e}")
            return _respond_error("Invalid quantity. Please enter a valid number greater than 0.", request.is_json, 400)

        cart = get_or_create_cart()
        if not cart:
            logger.error(f"Cart not found for user {current_user.id} when trying to update item {cart_item_id}")
            return _respond_error("Cart not found", request.is_json, 404)
        
        # Verify cart_id is set (get_or_create_cart should have already committed)
        if not cart.cart_id:
            logger.error(f"Cart ID is None in update_item for user {current_user.id}")
            return _respond_error("Cart not available. Please try again.", request.is_json, 500)

        item = CartItem.query.filter_by(
            cart_item_id=cart_item_id,
            cart_id=cart.cart_id
        ).first()

        if not item:
            logger.warning(f"Cart item {cart_item_id} not found in cart {cart.cart_id} for user {current_user.id}")
            if request.is_json:
                return jsonify(success=False, message="Item not found in cart"), 404
            flash("Item not found in cart", "warning")
            return redirect(url_for('cart.index'))

        # Validate stock before updating quantity
        if item.product and item.product.quantity is not None:
            if quantity > item.product.quantity:
                available = item.product.quantity
                product_name = item.product.product_name
                message = f"Insufficient stock for '{product_name}'. Available: {available}, Requested: {quantity}."
                logger.info(f"Stock check failed when updating cart item {cart_item_id}: available={available}, requested={quantity}")
                if request.is_json:
                    return jsonify(success=False, message=message), 400
                flash(message, "danger")
                return redirect(url_for('cart.index'))

        old_quantity = item.quantity
        item.quantity = quantity
        product_name = item.product.product_name if item.product else "Item"
        
        try:
            db.session.commit()
            logger.info(f"Updated cart item {cart_item_id} quantity from {old_quantity} to {quantity} for user {current_user.id}")

            if request.is_json:
                return jsonify(success=True, quantity=quantity, message=f"Updated {product_name} quantity to {quantity}")

            flash(f"Updated {product_name} quantity to {quantity}", "success")
            return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception(f"Error committing cart item update {cart_item_id}: {e}")
            db.session.rollback()
            return _respond_error("Error updating cart. Please try again.", request.is_json, 500)

    except Exception as e:
        logger.exception(f"Unexpected error updating cart item {cart_item_id} for user {current_user.id}: {e}")
        db.session.rollback()
        return _respond_error("Error updating cart. Please try again.", request.is_json, 500)


# -------------------------------------------------
# Buy Now (Single Item Checkout)
# -------------------------------------------------
@cart_bp.route('/buy_now/<int:cart_item_id>', methods=['POST'])
@login_required
def buy_now(cart_item_id):
    """
    Buy Now functionality - checkout with a single item immediately.
    Creates a temporary single-item cart and redirects to checkout.
    """
    try:
        user_id = getattr(current_user, 'id', None)
        if not user_id:
            logger.error("current_user.id is None in buy_now")
            flash("User session invalid. Please log in again.", "danger")
            return redirect(url_for('auth.login'))
        
        logger.info(f"=== BUY NOW: user_id={user_id}, cart_item_id={cart_item_id} ===")
        
        # Get the cart item
        cart = get_or_create_cart()
        if not cart or not cart.cart_id:
            logger.error(f"Cart not found for user {user_id} in buy_now")
            flash("Cart not found. Please try again.", "danger")
            return redirect(url_for('cart.index'))
        
        item = CartItem.query.filter_by(
            cart_item_id=cart_item_id,
            cart_id=cart.cart_id
        ).first()
        
        if not item:
            logger.warning(f"Cart item {cart_item_id} not found in cart {cart.cart_id} for user {user_id}")
            flash("Item not found in cart.", "warning")
            return redirect(url_for('cart.index'))
        
        # Verify product exists and is in stock
        product = Product.query.get(item.product_id)
        if not product:
            logger.warning(f"Product {item.product_id} not found for cart item {cart_item_id}")
            flash("Product not found.", "danger")
            return redirect(url_for('cart.index'))
        
        # Check stock
        if product.quantity is not None and item.quantity > product.quantity:
            flash(f"Insufficient stock. Available: {product.quantity}, Requested: {item.quantity}.", "danger")
            return redirect(url_for('cart.index'))
        
        # Store the cart_item_id in session for checkout to use
        session['buy_now_item_id'] = cart_item_id
        session['buy_now_cart_id'] = cart.cart_id
        logger.info(f"✓ Stored buy_now_item_id={cart_item_id} in session, redirecting to checkout")
        
        # Redirect to checkout - the checkout route will handle single item checkout
        return redirect(url_for('payment.checkout_payment', buy_now=cart_item_id))
        
    except Exception as e:
        logger.exception(f"Error in buy_now for user {getattr(current_user, 'id', 'unknown')}, cart_item_id={cart_item_id}: {e}")
        db.session.rollback()
        flash("Error processing Buy Now. Please try again.", "danger")
        return redirect(url_for('cart.index'))


# -------------------------------------------------
# Error helper
# -------------------------------------------------
def _respond_error(message, ajax=False, status_code=400):
    """Helper function to respond with error messages in JSON or flash format."""
    if ajax or (request.is_json if hasattr(request, 'is_json') else False):
        response = jsonify(success=False, message=message, error=message)
        response.status_code = status_code
        return response

    flash(message, "danger" if status_code >= 400 else "warning")
    try:
        return redirect(url_for('catalog.catalog'))
    except Exception as e:
        logger.warning(f"Error redirecting to catalog: {e}")
        try:
            return redirect(url_for('cart.index'))
        except Exception:
            return redirect(url_for('home'))
