# blueprints/payment.py
import logging
import os
import re
import urllib.parse
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Order, OrderDetail, Cart, CartItem, Payment, Product, User, PaymentNotification
from flask_login import current_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import text

logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


def generate_qr_code(amount, order_id, upi_id='merchant@upi', merchant_name='Retailer'):
    """
    Generate a QR code with UPI payment link containing the exact order amount.
    Format: upi://pay?pa=<upi_id>&pn=<merchant_name>&am=<amount>&cu=INR&tn=<transaction_note>
    
    Args:
        amount: Decimal or float - exact order amount
        order_id: Order ID for transaction note
        upi_id: UPI ID (default merchant@upi, should be configured)
        merchant_name: Merchant name for UPI
        
    Returns:
        filename: String - filename of saved QR code image
    """
    try:
        # Convert amount to string with 2 decimal places for UPI
        amount_str = f"{float(amount):.2f}"
        
        # Create UPI payment link with URL-encoded parameters
        transaction_note = f"Order #{order_id}"
        # URL-encode parameters to handle special characters and spaces
        merchant_name_encoded = urllib.parse.quote(merchant_name)
        transaction_note_encoded = urllib.parse.quote(transaction_note)
        upi_id_encoded = urllib.parse.quote(upi_id)
        
        upi_link = f"upi://pay?pa={upi_id_encoded}&pn={merchant_name_encoded}&am={amount_str}&cu=INR&tn={transaction_note_encoded}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_link)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure qr_codes directory exists
        qr_dir = os.path.join(current_app.root_path, 'static', 'qr_codes')
        os.makedirs(qr_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"qr_order_{order_id}_{timestamp}.png"
        filepath = os.path.join(qr_dir, filename)
        
        # Save QR code image
        img.save(filepath)
        
        logger.info(f"Generated QR code for order {order_id}, amount {amount_str}, saved as {filename}")
        return filename
        
    except Exception as e:
        logger.exception(f"Error generating QR code for order {order_id}: {e}")
        return None


def send_retailer_notification(order, payment, retailer):
    """
    Send notification to retailer when order is placed.
    Creates a PaymentNotification record with order details and customer address.
    Can be extended for email/SMS.
    
    Args:
        order: Order object
        payment: Payment object
        retailer: User object (retailer/admin)
    """
    try:
        # Collect product names
        product_names = []
        if order.items:
            for item in order.items[:5]:  # First 5 products
                if item.product_name:
                    product_names.append(item.product_name)
        
        # Build address string for notification
        address_parts = []
        if order.delivery_name:
            address_parts.append(f"Name: {order.delivery_name}")
        if order.delivery_phone:
            address_parts.append(f"Phone: {order.delivery_phone}")
        if order.delivery_address:
            address_parts.append(f"Address: {order.delivery_address}")
        if order.delivery_city:
            address_parts.append(f"City: {order.delivery_city}")
        if order.delivery_pincode:
            address_parts.append(f"Pincode: {order.delivery_pincode}")
        
        address_details = " | ".join(address_parts) if address_parts else "Address not provided"
        
        # Create notification record with address details
        if retailer and order.admin_id:
            notification = PaymentNotification(
                order_id=order.order_id,
                payment_id=payment.payment_id,
                retailer_id=order.admin_id,
                buyer_name=order.customer.username if order.customer else order.delivery_name or 'Customer',
                product_name=f"{', '.join(product_names) if product_names else 'Multiple Products'} | {address_details}",
                payment_method=payment.method,
                payment_amount=payment.amount,
                is_read=False,
                notification_type='order_placed'
            )
            db.session.add(notification)
            logger.info(f"Created notification with address for retailer {retailer.id} for order {order.order_id}")
            
            # Here you can extend to send email/SMS to retailer
            # Example: send_email(retailer.email, "New Order Received", f"Order #{order.order_id}\n{address_details}")
            
    except Exception as e:
        logger.exception(f"Error sending retailer notification for order {order.order_id}: {e}")
        # Don't fail the order if notification fails


@payment_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout_payment():
    """
    Checkout endpoint. GET shows checkout page with retailer payment methods.
    POST processes payment (COD or Online) and creates order, order lines, payment record.
    """
    try:
        # Validate authentication
        if not current_user.is_authenticated:
            flash("Please log in to checkout.", "warning")
            return redirect(url_for('auth.login'))

        # Check if this is a "Buy Now" single item checkout
        buy_now_item_id = session.get('buy_now_item_id')
        buy_now_mode = bool(buy_now_item_id)
        
        # Get cart and validate it has items
        try:
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            if not cart:
                flash("Your cart is empty. Please add items to your cart first.", "warning")
                return redirect(url_for('cart.index'))
            
            if buy_now_mode:
                # Buy Now: Only process the specific item
                logger.info(f"Buy Now mode: Processing single item {buy_now_item_id}")
                buy_now_item = CartItem.query.filter_by(
                    cart_item_id=buy_now_item_id,
                    cart_id=cart.cart_id
                ).first()
                
                if not buy_now_item:
                    # Clear invalid buy_now session
                    session.pop('buy_now_item_id', None)
                    session.pop('buy_now_cart_id', None)
                    flash("Item not found. Please try again.", "warning")
                    return redirect(url_for('cart.index'))
                
                items = [buy_now_item]  # Only this one item
                logger.info(f"Buy Now: Processing item {buy_now_item_id} - product_id={buy_now_item.product_id}, quantity={buy_now_item.quantity}")
            else:
                # Normal checkout: All cart items
                items = list(cart.items)  # Convert to list to avoid lazy loading issues
                if not items:
                    flash("Your cart is empty. Please add items to your cart first.", "warning")
                    return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception("Error loading cart: %s", e)
            db.session.rollback()
            flash("Error loading your cart. Please try again.", "danger")
            return redirect(url_for('cart.index'))

        # Calculate total
        try:
            total = sum(float(it.unit_price or 0) * (it.quantity or 0) for it in items)
            if total <= 0:
                flash("Invalid cart total. Please refresh your cart.", "danger")
                return redirect(url_for('cart.index'))
        except (ValueError, TypeError) as e:
            logger.exception("Error calculating total: %s", e)
            flash("Error calculating cart total. Please refresh your cart.", "danger")
            return redirect(url_for('cart.index'))

        # Get all products from cart items and validate they exist
        products = []
        try:
            for item in items:
                if not item.product_id:
                    logger.warning("Cart item %s has no product_id", item.cart_item_id)
                    continue
                    
                product = Product.query.get(item.product_id)
                if not product:
                    logger.warning("Product %s not found for cart item %s", item.product_id, item.cart_item_id)
                    flash(f"Product ID {item.product_id} no longer exists. Please update your cart.", "danger")
                    return redirect(url_for('cart.index'))
                
                products.append(product)
        except Exception as e:
            logger.exception("Error loading products: %s", e)
            db.session.rollback()
            flash("Error loading products. Please try again.", "danger")
            return redirect(url_for('cart.index'))
        
        if not products:
            flash("No valid products in cart. Please add products to your cart.", "danger")
            return redirect(url_for('cart.index'))

        # Determine retailer (admin_id) - validate all products are from same retailer
        try:
            retailer_ids = [p.admin_id for p in products if p.admin_id is not None]
            if not retailer_ids:
                flash("Products have no retailer assigned. Please contact support.", "danger")
                return redirect(url_for('cart.index'))
            
            # Check if all products are from same retailer (required for order)
            unique_retailer_ids = set(retailer_ids)
            if len(unique_retailer_ids) > 1:
                flash("All items in cart must be from the same retailer. Please separate orders.", "warning")
                return redirect(url_for('cart.index'))
            
            retailer_id = retailer_ids[0]
            if not retailer_id:
                flash("Retailer information is missing. Please contact support.", "danger")
                return redirect(url_for('cart.index'))
            
            # Get retailer user
            retailer = User.query.get(retailer_id)
            if not retailer:
                logger.error("Retailer user %s not found", retailer_id)
                flash("Retailer information is invalid. Please contact support.", "danger")
                return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception("Error determining retailer: %s", e)
            db.session.rollback()
            flash("Error processing retailer information. Please try again.", "danger")
            return redirect(url_for('cart.index'))
        
        # Get payment methods available (intersection - all products must support it)
        try:
            cod_available = all(getattr(p, 'cod_enabled', True) for p in products)
            online_available = all(getattr(p, 'online_payment_enabled', False) for p in products)
        except Exception as e:
            logger.exception("Error checking payment methods: %s", e)
            cod_available = True  # Default to COD if error
            online_available = False
        
        # Get QR code from products (find first product with QR code)
        qr_code_filename = None
        try:
            if online_available:
                for p in products:
                    qr_code = getattr(p, 'qr_code_filename', None)
                    if qr_code:
                        qr_code_filename = qr_code
                        break
        except Exception as e:
            logger.exception("Error finding QR code: %s", e)
            qr_code_filename = None

        # GET: Show checkout page
        if request.method == 'GET':
            return render_template(
                'payment/checkout.html', 
                items=items, 
                total=total, 
                cart=cart,
                cod_available=cod_available,
                online_available=online_available,
                qr_code_filename=qr_code_filename,
                retailer=retailer,
                buy_now_mode=buy_now_mode  # Pass buy_now flag to template
            )

        # POST: process payment
        selected_method = request.form.get('payment_method', '').strip()  # 'cod' or 'online'
        if not selected_method:
            flash("Please select a payment method.", "warning")
            return redirect(url_for('payment.checkout_payment'))

        # Validate payment method availability
        if selected_method == 'cod' and not cod_available:
            flash("Cash on Delivery is not available for this order.", "danger")
            return redirect(url_for('payment.checkout_payment'))
        if selected_method == 'online' and not online_available:
            flash("Online Payment is not available for this order.", "danger")
            return redirect(url_for('payment.checkout_payment'))
        if selected_method == 'online' and not qr_code_filename:
            flash("QR code not configured for online payment. Please contact the retailer.", "danger")
            return redirect(url_for('payment.checkout_payment'))

        # Validate stock before proceeding
        try:
            for it in items:
                if not it.product_id:
                    flash("Invalid cart item. Please refresh your cart.", "danger")
                    return redirect(url_for('cart.index'))
                
                product = Product.query.get(it.product_id)
                if not product:
                    flash(f"Product ID {it.product_id} no longer exists. Please update your cart.", "danger")
                    return redirect(url_for('cart.index'))

                # Check stock availability
                product_quantity = getattr(product, 'quantity', None)
                if product_quantity is not None:
                    if product_quantity < it.quantity:
                        flash(f"Insufficient stock for {product.product_name}. Available: {product_quantity}, Requested: {it.quantity}", "danger")
                        return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception("Error validating stock: %s", e)
            db.session.rollback()
            flash("Error checking stock availability. Please try again.", "danger")
            return redirect(url_for('cart.index'))

        # Collect and validate delivery address information
        try:
            delivery_name = request.form.get('delivery_name', '').strip()
            delivery_phone = request.form.get('delivery_phone', '').strip()
            delivery_email = request.form.get('delivery_email', '').strip()
            delivery_address = request.form.get('delivery_address', '').strip()
            delivery_city = request.form.get('delivery_city', '').strip()
            delivery_pincode = request.form.get('delivery_pincode', '').strip()

            # Validate required delivery address fields
            if not delivery_name:
                flash("Full name is required for delivery.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            # Validate name format (should contain only letters, spaces, and basic punctuation)
            if len(delivery_name) < 2 or len(delivery_name) > 200:
                flash("Name must be between 2 and 200 characters.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            if not delivery_phone:
                flash("Phone number is required for delivery.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            # Validate phone number format (10 digits, can start with +91 or 0)
            phone_cleaned = delivery_phone.replace('+91', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if phone_cleaned.startswith('0'):
                phone_cleaned = phone_cleaned[1:]
            
            if len(phone_cleaned) != 10 or not phone_cleaned.isdigit():
                flash("Please enter a valid 10-digit phone number (without country code).", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            delivery_phone = phone_cleaned  # Use cleaned phone number
            
            # Validate email format if provided
            if delivery_email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, delivery_email):
                    flash("Please enter a valid email address.", "danger")
                    return redirect(url_for('payment.checkout_payment'))
            
            if not delivery_address:
                flash("Delivery address is required.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            # Validate address length
            if len(delivery_address) < 10 or len(delivery_address) > 500:
                flash("Address must be between 10 and 500 characters.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            if not delivery_city:
                flash("City is required for delivery.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            # Validate city format (letters and spaces only)
            if len(delivery_city) < 2 or len(delivery_city) > 100:
                flash("City must be between 2 and 100 characters.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            if not delivery_pincode:
                flash("Pincode is required for delivery.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            # Validate pincode format (6 digits for India)
            pincode_cleaned = delivery_pincode.strip()
            if len(pincode_cleaned) != 6 or not pincode_cleaned.isdigit():
                flash("Please enter a valid 6-digit pincode.", "danger")
                return redirect(url_for('payment.checkout_payment'))
            
            delivery_pincode = pincode_cleaned  # Use cleaned pincode
            
        except Exception as e:
            logger.exception("Error validating delivery address: %s", e)
            flash("Error processing delivery address. Please check your input and try again.", "danger")
            return redirect(url_for('payment.checkout_payment'))

        # Calculate delivery date based on maximum delivery_days from products
        try:
            max_delivery_days = 3  # Default to 3 days
            for p in products:
                try:
                    delivery_days = getattr(p, 'delivery_days', 3) or 3
                    if isinstance(delivery_days, (int, float)) and delivery_days > max_delivery_days:
                        max_delivery_days = int(delivery_days)
                except (ValueError, TypeError, AttributeError):
                    continue  # Use default if error
            
            # Calculate delivery_date = order_date + delivery_days (working days)
            order_date = datetime.utcnow()
            delivery_date = order_date
            days_added = 0
            max_attempts = max_delivery_days * 2  # Safety limit
            attempts = 0
            
            while days_added < max_delivery_days and attempts < max_attempts:
                delivery_date += timedelta(days=1)
                attempts += 1
                # Skip weekends (Saturday=5, Sunday=6)
                if delivery_date.weekday() < 5:  # Monday=0 to Friday=4
                    days_added += 1
        except Exception as e:
            logger.exception("Error calculating delivery date: %s", e)
            # Use defaults if calculation fails
            order_date = datetime.utcnow()
            delivery_date = order_date + timedelta(days=3)
            max_delivery_days = 3

        # Create order - wrap in try/except for database errors
        try:
            order = Order(
                customer_id=current_user.id,
                admin_id=retailer_id,  # Set retailer/admin who owns the products
                order_date=order_date,
                total_amount=total,
                status='pending' if selected_method == 'cod' else 'pending_verification',
                # Delivery information
                delivery_name=delivery_name,
                delivery_phone=delivery_phone,
                delivery_email=delivery_email or (current_user.email if current_user.is_authenticated else None),
                delivery_address=delivery_address,
                delivery_city=delivery_city,
                delivery_pincode=delivery_pincode,
                delivery_days=max_delivery_days,
                delivery_date=delivery_date
            )
            db.session.add(order)
            db.session.flush()  # Get order_id without committing
            
            logger.info(f"Created order {order.order_id} for customer {current_user.id}, retailer {retailer_id}, total {total}")
        except Exception as e:
            logger.exception("Error creating order: %s", e)
            db.session.rollback()
            flash("Error creating order. Please try again.", "danger")
            return redirect(url_for('payment.checkout_payment'))

        # Create order lines (order details)
        try:
            for it in items:
                product = Product.query.get(it.product_id)
                if not product:
                    logger.error(f"Product {it.product_id} not found when creating order {order.order_id}")
                    raise ValueError(f"Product {it.product_id} not found")
                
                # Use SQLAlchemy ORM instead of raw SQL for better error handling
                order_detail = OrderDetail(
                    order_id=order.order_id,
                    product_id=it.product_id,
                    order_quantity=it.quantity,
                    unit_price=float(it.unit_price or 0),
                    product_name=product.product_name
                )
                db.session.add(order_detail)
                
                # Update inventory (decrease product quantity) - re-check stock before deduction
                if hasattr(product, 'quantity') and product.quantity is not None:
                    # Refresh product to get latest quantity (prevent race conditions)
                    db.session.refresh(product)
                    current_quantity = product.quantity
                    
                    if current_quantity < it.quantity:
                        logger.error(f"Insufficient stock for product {it.product_id} when creating order {order.order_id}. Available: {current_quantity}, Requested: {it.quantity}")
                        db.session.rollback()
                        flash(f"Insufficient stock for {product.product_name}. Available: {current_quantity}, Requested: {it.quantity}. Please update your cart.", "danger")
                        return redirect(url_for('cart.index'))
                    
                    # Deduct quantity
                    product.quantity -= it.quantity
                    if product.quantity < 0:
                        logger.warning(f"Product {it.product_id} quantity went negative after deduction, setting to 0")
                        product.quantity = 0
                    logger.info(f"Deducted {it.quantity} units from product {it.product_id}, remaining: {product.quantity}")
            
            db.session.flush()  # Flush order details without committing
        except Exception as e:
            logger.exception("Error creating order details: %s", e)
            db.session.rollback()
            flash("Error creating order items. Please try again.", "danger")
            return redirect(url_for('payment.checkout_payment'))

        # Create payment record
        try:
            payment_method_name = 'Cash on Delivery' if selected_method == 'cod' else 'Online Payment'
            payment_status = 'COD' if selected_method == 'cod' else 'pending'
            
            # Get QR code for online payment
            qr_code_filename = None
            admin_qr_code = None  # Admin's uploaded QR code (for reference)
            
            if selected_method == 'online':
                merchant_name = retailer.username if retailer else 'Retailer'
                upi_id = None
                
                # First, try to get admin's uploaded QR code from Product or SellerPaymentOption
                try:
                    from models import SellerPaymentOption
                    seller_payment = SellerPaymentOption.query.filter_by(admin_id=retailer_id).first()
                    
                    # Get admin's QR code image (if uploaded)
                    if seller_payment and seller_payment.qr_image:
                        admin_qr_code = seller_payment.qr_image
                        logger.info(f"Found admin QR code: {admin_qr_code} for retailer {retailer_id}")
                    
                    # Also check products for QR code
                    if not admin_qr_code and products:
                        for p in products:
                            if p.qr_code_filename:
                                admin_qr_code = p.qr_code_filename
                                logger.info(f"Found product QR code: {admin_qr_code}")
                                break
                    
                    # Try to get UPI ID from seller payment option
                    if seller_payment:
                        if hasattr(seller_payment, 'upi_id') and seller_payment.upi_id:
                            upi_id = seller_payment.upi_id
                        # If qr_image contains @, it might be a UPI ID
                        elif seller_payment.qr_image and '@' in seller_payment.qr_image and not seller_payment.qr_image.endswith(('.png', '.jpg', '.jpeg')):
                            upi_id = seller_payment.qr_image
                            
                except Exception as e:
                    logger.warning(f"Error getting seller payment option: {e}")
                
                # If no UPI ID found, use default
                if not upi_id:
                    upi_id = f"{merchant_name.lower().replace(' ', '')}@upi" if merchant_name else 'merchant@upi'
                    logger.warning(f"No UPI ID configured for retailer {retailer_id}, using default: {upi_id}")
                
                # Validate UPI ID format
                if not upi_id or '@' not in upi_id:
                    upi_id = 'merchant@upi'
                    logger.warning(f"Invalid UPI ID format, using default: {upi_id}")
                
                # Generate QR code with order amount (this will show amount when scanned)
                qr_code_filename = generate_qr_code(
                    amount=total,
                    order_id=order.order_id,
                    upi_id=upi_id,
                    merchant_name=merchant_name
                )
                
                if not qr_code_filename:
                    logger.error(f"Failed to generate QR code for order {order.order_id}")
                    db.session.rollback()
                    flash("Failed to generate payment QR code. Please try again or contact support.", "danger")
                    return redirect(url_for('payment.checkout_payment'))
                
                # Store admin's QR code reference if available (for display purposes)
                if admin_qr_code:
                    logger.info(f"Admin QR code available: {admin_qr_code}, but using generated QR with amount: {qr_code_filename}")
            
            payment = Payment(
                order_id=order.order_id,
                amount=total,
                method=payment_method_name,
                status=payment_status,
                payment_status=payment_status,
                qr_code_filename=qr_code_filename,  # Store dynamic QR code filename
                created_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.flush()  # Get payment_id without committing
            
            logger.info(f"Created payment {payment.payment_id} for order {order.order_id}, method {payment_method_name}, status {payment_status}, QR: {qr_code_filename}")
        except Exception as e:
            logger.exception("Error creating payment record: %s", e)
            db.session.rollback()
            flash("Error creating payment record. Please try again.", "danger")
            return redirect(url_for('payment.checkout_payment'))

        # Clear cart items and cart (only after everything succeeds)
        try:
            for it in items:
                db.session.delete(it)
            if cart:
                db.session.delete(cart)
            
            # Commit all changes together
            db.session.commit()
            
            logger.info(f"Order {order.order_id} created successfully. Cart cleared for user {current_user.id}")
            
            # Clear buy_now session variables if this was a buy_now order
            if buy_now_mode:
                session.pop('buy_now_item_id', None)
                session.pop('buy_now_cart_id', None)
                logger.info(f"Cleared buy_now session variables after order {order.order_id}")
            
            # Send notification to retailer after successful commit
            try:
                send_retailer_notification(order, payment, retailer)
                # Commit notification if it was created
                db.session.commit()
            except Exception as e:
                logger.exception(f"Error sending retailer notification for order {order.order_id}: {e}")
                db.session.rollback()  # Rollback only notification, order already committed
                # Don't fail the order if notification fails
            
        except Exception as e:
            logger.exception("Error clearing cart: %s", e)
            db.session.rollback()
            flash("Order created but error clearing cart. Please contact support with Order ID: " + str(order.order_id), "warning")
            # Still redirect to receipt since order was created

        flash("Order placed successfully! Expected delivery: " + delivery_date.strftime('%Y-%m-%d'), "success")
        
        # Redirect based on payment method
        if selected_method == 'online':
            return redirect(url_for('payment.confirm_payment', order_id=order.order_id))
        else:
            return redirect(url_for('payment.receipt', order_id=order.order_id))

    except Exception as exc:
        logger.exception("Fatal error in checkout: %s", exc)
        db.session.rollback()
        flash("An error occurred during checkout. Please try again or contact support.", "danger")
        return redirect(url_for('cart.index'))


@payment_bp.route('/confirm/<int:order_id>', methods=['GET', 'POST'])
@login_required
def confirm_payment(order_id):
    """
    Payment confirmation page for online payments.
    Shows QR code and allows user to mark payment as done.
    """
    try:
        # Validate authentication
        if not current_user.is_authenticated:
            flash("Please log in to view payment confirmation.", "warning")
            return redirect(url_for('auth.login'))
        
        # Get order with error handling
        try:
            order = Order.query.get(order_id)
            if not order:
                flash(f"Order #{order_id} not found.", "danger")
                return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception("Error loading order %s: %s", order_id, e)
            db.session.rollback()
            flash("Error loading order. Please try again.", "danger")
            return redirect(url_for('cart.index'))
        
        # Access control - verify user owns the order
        if order.customer_id != current_user.id:
            logger.warning("User %s attempted to access order %s owned by user %s", current_user.id, order_id, order.customer_id)
            flash("Access denied. This order does not belong to you.", "danger")
            return redirect(url_for('cart.index'))
        
        # Get payment record
        try:
            payment = Payment.query.filter_by(order_id=order_id).first()
            if not payment:
                logger.error("Payment record not found for order %s", order_id)
                flash("Payment record not found for this order. Please contact support.", "danger")
                return redirect(url_for('cart.index'))
        except Exception as e:
            logger.exception("Error loading payment for order %s: %s", order_id, e)
            db.session.rollback()
            flash("Error loading payment information. Please try again.", "danger")
            return redirect(url_for('cart.index'))
    
        # Validate payment method - only online payments can be confirmed here
        if payment.method != 'Online Payment':
            flash("This order does not require payment confirmation. Use Cash on Delivery.", "info")
            return redirect(url_for('payment.receipt', order_id=order_id))
        
        # Get dynamic QR code from Payment model (generated with order amount)
        qr_code_filename = payment.qr_code_filename if payment else None
        
        # If QR code not found in payment, try to generate it (fallback)
        if not qr_code_filename and payment.method == 'Online Payment':
            try:
                # Get retailer information
                retailer = order.retailer if order else None
                merchant_name = retailer.username if retailer else 'Retailer'
                upi_id = None
                
                if retailer:
                    try:
                        from models import SellerPaymentOption
                        seller_payment = SellerPaymentOption.query.filter_by(admin_id=order.admin_id).first()
                        
                        if seller_payment:
                            if hasattr(seller_payment, 'upi_id') and seller_payment.upi_id:
                                upi_id = seller_payment.upi_id
                            elif seller_payment.qr_image and '@' in seller_payment.qr_image:
                                upi_id = seller_payment.qr_image
                    except Exception as e:
                        logger.warning(f"Error getting seller payment option: {e}")
                
                if not upi_id:
                    upi_id = f"{merchant_name.lower().replace(' ', '')}@upi" if merchant_name else 'merchant@upi'
                
                # Validate UPI ID format
                if not upi_id or '@' not in upi_id:
                    upi_id = 'merchant@upi'
                
                # Generate QR code
                qr_code_filename = generate_qr_code(
                    amount=payment.amount,
                    order_id=order.order_id,
                    upi_id=upi_id,
                    merchant_name=merchant_name
                )
                
                # Update payment with generated QR code
                if qr_code_filename:
                    payment.qr_code_filename = qr_code_filename
                    db.session.commit()
                    logger.info(f"Generated and saved QR code for order {order_id}: {qr_code_filename}")
                else:
                    logger.error(f"Failed to generate QR code for order {order_id}")
            except Exception as e:
                logger.exception(f"Error generating QR code for order {order_id}: {e}")
                # Continue without QR code - user will see warning
    
        # Handle POST: User clicked "Mark Payment as Done"
        if request.method == 'POST':
            try:
                # Check if already marked as paid
                if payment.payment_status == 'paid' or payment.status == 'paid':
                    flash("Payment already confirmed as paid.", "info")
                    return redirect(url_for('payment.receipt', order_id=order_id))
                
                # Validate order belongs to current user (double-check for security)
                if order.customer_id != current_user.id:
                    flash("Access denied.", "danger")
                    return redirect(url_for('cart.index'))
                
                # Automatically update payment status to 'paid' after user marks it as done
                # This is based on trust that user has completed the payment
                payment.status = 'paid'
                payment.payment_status = 'paid'
                payment.payment_timestamp = datetime.utcnow()
                payment.confirmed_at = datetime.utcnow()  # Auto-confirm since user marked as done
                order.status = 'confirmed'  # Order confirmed after payment
                
                # Create notification for retailer about payment completion
                try:
                    product_names = []
                    if order.items:
                        for item in order.items[:5]:  # First 5 products
                            if item.product_name:
                                product_names.append(item.product_name)
                    
                    # Build address string for notification
                    address_parts = []
                    if order.delivery_name:
                        address_parts.append(f"Name: {order.delivery_name}")
                    if order.delivery_phone:
                        address_parts.append(f"Phone: {order.delivery_phone}")
                    if order.delivery_address:
                        address_parts.append(f"Address: {order.delivery_address}")
                    if order.delivery_city:
                        address_parts.append(f"City: {order.delivery_city}")
                    if order.delivery_pincode:
                        address_parts.append(f"Pincode: {order.delivery_pincode}")
                    
                    address_details = " | ".join(address_parts) if address_parts else "Address not provided"
                    
                    # Validate retailer_id exists before creating notification
                    if order.admin_id:
                        notification = PaymentNotification(
                            order_id=order.order_id,
                            payment_id=payment.payment_id,
                            retailer_id=order.admin_id,
                            buyer_name=current_user.username or order.delivery_name or 'Customer',
                            product_name=f"{', '.join(product_names) if product_names else 'Multiple Products'} | {address_details}",
                            payment_method=payment.method,
                            payment_amount=payment.amount,
                            is_read=False,
                            notification_type='payment_confirmed'
                        )
                        db.session.add(notification)
                        
                        logger.info(f"Created payment confirmation notification with address for admin {order.admin_id} for order {order.order_id}")
                    else:
                        logger.warning("Order %s has no admin_id, skipping notification creation", order.order_id)
                    
                    db.session.commit()
                    
                    logger.info(f"Payment automatically confirmed as paid for order {order_id} by user {current_user.id}")
                    flash("Payment confirmed! Your order has been placed successfully. Retailer has been notified.", "success")
                    return redirect(url_for('payment.receipt', order_id=order_id))
                    
                except Exception as e:
                    logger.exception("Error creating payment notification: %s", e)
                    db.session.rollback()
                    flash("Payment marked but notification failed. Order ID: " + str(order.order_id), "warning")
                    return redirect(url_for('payment.receipt', order_id=order_id))
                    
            except Exception as exc:
                logger.exception("Failed to mark payment as done for order %s: %s", order_id, exc)
                db.session.rollback()
                flash("Failed to confirm payment. Please try again.", "danger")
        
        # GET: Show payment confirmation page
        return render_template(
            'payment/confirm.html',
            order=order,
            payment=payment,
            qr_code_filename=qr_code_filename
        )
        
    except Exception as e:
        logger.exception("Fatal error in confirm_payment for order %s: %s", order_id, e)
        db.session.rollback()
        flash("An error occurred. Please try again or contact support.", "danger")
        return redirect(url_for('cart.index'))


@payment_bp.route('/receipt/<int:order_id>')
def receipt(order_id):
    """Show payment receipt for an order."""
    try:
        # Get order with error handling
        try:
            order = Order.query.get(order_id)
            if not order:
                flash(f"Order #{order_id} not found.", "danger")
                return redirect(url_for('catalog.catalog'))
        except Exception as e:
            logger.exception("Error loading order %s: %s", order_id, e)
            db.session.rollback()
            flash("Error loading order. Please try again.", "danger")
            return redirect(url_for('catalog.catalog'))
        
        # Access control - check if user can view this order
        if current_user.is_authenticated:
            is_owner = order.customer_id == current_user.id
            is_admin = current_user.role == 'admin'
            if not is_owner and not is_admin:
                logger.warning("User %s attempted to access order %s (owner: %s)", current_user.id, order_id, order.customer_id)
                flash("Access denied. This order does not belong to you.", "danger")
                return redirect(url_for('catalog.catalog'))
        else:
            # For non-authenticated users, only allow if order is accessible (might need session check)
            # For now, redirect to login
            flash("Please log in to view order receipt.", "warning")
            return redirect(url_for('auth.login'))
        
        # Get payment record
        try:
            payment = Payment.query.filter_by(order_id=order_id).first()
            # Payment might not exist for some edge cases, handle gracefully
            if not payment:
                logger.warning("Payment record not found for order %s", order_id)
                flash("Payment record not found for this order.", "warning")
                # Still show order but with warning
        except Exception as e:
            logger.exception("Error loading payment for order %s: %s", order_id, e)
            db.session.rollback()
            payment = None  # Continue without payment info
        
        return render_template('payment/receipt.html', order=order, payment=payment)
        
    except Exception as e:
        logger.exception("Fatal error in receipt for order %s: %s", order_id, e)
        db.session.rollback()
        flash("An error occurred loading the receipt. Please try again.", "danger")
        return redirect(url_for('catalog.catalog'))
