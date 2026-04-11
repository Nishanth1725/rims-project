# Payment Flow Guide

## Overview
The payment system supports two payment methods:
1. **Cash on Delivery (COD)** - Payment made when the order is delivered
2. **Online Payment (QR Code)** - Payment via UPI QR code scan

---

## Complete Payment Flow

### Step 1: Add Items to Cart
- User browses products and clicks "Add to Cart"
- Items are stored in the `cart_item` table with:
  - `cart_id` (links to user's cart)
  - `product_id` (product being purchased)
  - `quantity` (number of items)
  - `unit_price` (price at time of adding to cart)

### Step 2: View Cart
- User clicks "Cart" to view all items
- Cart page shows:
  - Product name, image, quantity
  - Unit price and subtotal per item
  - Total cart amount
  - Options to update quantity or remove items

### Step 3: Proceed to Checkout
- User clicks "Proceed to Checkout" button
- Route: `/payment/checkout` (GET request)
- System:
  1. Validates cart has items
  2. Calculates total amount
  3. Checks which payment methods are available (COD/Online)
  4. Retrieves QR code if online payment is available
  5. Shows checkout form with:
     - Delivery address fields (name, phone, street, city, pincode)
     - Payment method selection (COD or Online)
     - Order summary

### Step 4: Fill Delivery Address
User must provide:
- **Full Name** (required, 2-200 characters)
- **Phone Number** (required, 10 digits)
- **Street Address** (required, 2-500 characters)
- **City** (required, 2-100 characters)
- **Pincode** (required, 6 digits)

### Step 5: Select Payment Method

#### Option A: Cash on Delivery (COD)
- User selects "Cash on Delivery"
- Payment status: `pending`
- Order status: `pending`
- Payment is completed when order is delivered
- No QR code needed

#### Option B: Online Payment (QR Code)
- User selects "Online Payment"
- System generates a QR code with:
  - **Exact order amount** (e.g., ₹1,234.56)
  - UPI payment link format: `upi://pay?pa=<merchant_upi_id>&pn=<merchant_name>&am=<amount>&cu=INR&tn=Order #<order_id>`
  - QR code saved in `static/qr_codes/` directory
- User scans QR code with PhonePe, GooglePay, Paytm, etc.
- When scanned, the payment app shows the exact order amount
- User completes payment in their payment app
- Payment status: Initially `pending`, updated to `completed` after payment
- Order status: `pending` until payment confirmed

### Step 6: Submit Order
- User clicks "Place Order" button
- Route: `/payment/checkout` (POST request)
- System processes:
  1. **Validates all inputs** (address, payment method, stock availability)
  2. **Creates Order record** in `order` table:
     - `customer_id` (user who placed order)
     - `order_date` (current timestamp)
     - `delivery_name`, `delivery_phone`, `delivery_street`, `delivery_city`, `delivery_pincode`
     - `status` (default: `pending`)
     - `total_amount` (calculated from cart items)
  3. **Creates OrderDetail records** for each product:
     - `order_id` (links to order)
     - `product_id`, `product_name`, `order_quantity`, `unit_price`
  4. **Creates Payment record**:
     - `order_id` (links to order)
     - `amount` (total order amount)
     - `method` (`Cash on Delivery` or `Online QR`)
     - `status` (`pending` for COD, `pending` for Online until payment confirmed)
     - `qr_code_filename` (if online payment)
  5. **Deducts stock** from `product.quantity` for each item
  6. **Clears cart** (deletes cart items and cart)
  7. **Sends notification to retailer**:
     - Creates `PaymentNotification` record with:
       - Order details (order_id, total_amount)
       - Customer address (name, phone, street, city, pincode)
       - Payment method and status
       - Product list
       - Timestamp
     - Can be extended for email/SMS notifications

### Step 7: Order Confirmation

#### For COD Orders:
- Redirects to: `/payment/receipt/<order_id>`
- Shows order confirmation with:
  - Order ID
  - Delivery address
  - Expected delivery date (calculated from `product.delivery_days`)
  - Payment method: Cash on Delivery
  - Order status: Pending

#### For Online Payment Orders:
- Redirects to: `/payment/confirm/<order_id>`
- Shows:
  - QR code image (scannable)
  - Order amount
  - Instructions to scan and pay
  - After payment, user can mark payment as completed
  - Or admin can update payment status manually

### Step 8: Payment Status Updates

#### Manual Update (Admin):
- Admin can view all payments at `/admin/payments`
- Admin can confirm payment: `/admin/payments/confirm/<payment_id>`
- Updates `Payment.status` to `completed`
- Updates `Order.status` to `confirmed`

#### Automatic Update (Future Enhancement):
- Can integrate with payment gateway webhooks
- When payment is confirmed, automatically update status

---

## Database Tables Involved

### `cart` and `cart_item`
- Stores items before checkout
- Cleared after successful order creation

### `order`
- Main order record with customer and delivery info
- Status: `pending`, `confirmed`, `shipped`, `delivered`, `cancelled`

### `order_detail`
- Individual products in the order
- Stores product info at time of order (price, name)

### `payment`
- Payment record linked to order
- Status: `pending`, `completed`, `failed`
- Method: `Cash on Delivery` or `Online QR`
- Contains QR code filename if online payment

### `payment_notification`
- Notifications sent to retailer
- Contains order summary and customer address

---

## Key Features

### 1. Stock Validation
- Before checkout, system validates:
  - All products are still in stock
  - Requested quantities don't exceed available stock
  - If stock is insufficient, shows error and prevents checkout

### 2. Price Locking
- Product prices are stored in `cart_item.unit_price` when added to cart
- Prices are stored in `order_detail.unit_price` when order is created
- This ensures price changes don't affect existing orders

### 3. QR Code Generation
- QR codes are generated dynamically for each order
- Contains exact amount, merchant UPI ID, and order reference
- Saved as PNG images in `static/qr_codes/`
- Format: `qr_order_<order_id>_<timestamp>.png`

### 4. Delivery Date Calculation
- Calculated from `product.delivery_days` field
- Uses maximum delivery days from all products in order
- Example: If products have 3, 5, and 7 days, uses 7 days

### 5. Retailer Notifications
- Automatic notification when order is placed
- Contains all order details and customer address
- Can be extended for email/SMS integration

---

## Routes Summary

| Route | Method | Purpose |
|-------|--------|---------|
| `/cart/` | GET | View cart items |
| `/cart/add` | POST | Add item to cart |
| `/cart/update/<id>` | POST | Update item quantity |
| `/cart/remove/<id>` | POST | Remove item from cart |
| `/payment/checkout` | GET | Show checkout form |
| `/payment/checkout` | POST | Process order and payment |
| `/payment/receipt/<order_id>` | GET | Show order receipt (COD) |
| `/payment/confirm/<order_id>` | GET | Show payment confirmation (Online) |
| `/admin/payments` | GET | View all payments (Admin) |
| `/admin/payments/confirm/<id>` | POST | Confirm payment (Admin) |

---

## Error Handling

- **Empty Cart**: Redirects to cart page with warning
- **Invalid Stock**: Shows error, prevents checkout
- **Missing Address**: Form validation prevents submission
- **Payment Method Unavailable**: Shows error if method not available
- **Database Errors**: Rolls back transaction, shows error message
- **QR Code Generation Failure**: Falls back to COD if QR generation fails

---

## Security Features

- **CSRF Protection**: All forms use CSRF tokens
- **Authentication Required**: All payment routes require login
- **Stock Validation**: Prevents overselling
- **Price Locking**: Prevents price manipulation
- **Transaction Safety**: Uses database transactions for atomicity

---

## Future Enhancements

1. **Payment Gateway Integration**: Real-time payment status updates
2. **Email/SMS Notifications**: Automated notifications to customers and retailers
3. **Order Tracking**: Track order status and delivery updates
4. **Multiple Payment Methods**: Credit card, net banking, wallet
5. **Partial Payments**: Support for partial payments or installments
6. **Refund Processing**: Handle refunds for cancelled orders
