# Pre-Submission Checklist

Use this checklist to verify everything is working before submission.

## ✅ Setup Verification

- [ ] PostgreSQL is installed and running
- [ ] Database `rims_db` is created
- [ ] `DATABASE_URL` environment variable is set (or using SQLite for testing)
- [ ] Virtual environment is activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Database tables created (`python setup_database.py`)
- [ ] Sample data seeded (`python seed_data.py`)

## ✅ Application Testing

### Authentication
- [ ] Can register as a new customer
- [ ] Can login as customer
- [ ] Can login as admin (username: `admin`, password: `admin123`)
- [ ] Can logout
- [ ] Admin-only routes are protected

### Product Management
- [ ] Can view product catalog (`/catalog/`)
- [ ] Can create products (admin)
- [ ] Can edit products (admin)
- [ ] Can delete products (admin)
- [ ] Product images upload correctly

### Shopping Cart
- [ ] Can add products to cart
- [ ] Can view cart (`/cart/`)
- [ ] Can update cart item quantities
- [ ] Can remove items from cart
- [ ] Cart total calculates correctly

### Orders & Payment
- [ ] Can checkout from cart
- [ ] Payment creates order successfully
- [ ] Receipt page displays correctly
- [ ] Orders appear in user dashboard

### Inventory Management
- [ ] Can view inventory (`/inventory/`)
- [ ] Can add inventory entries
- [ ] Can adjust inventory quantities
- [ ] Low stock alerts work

### Warehouse Management
- [ ] Can view warehouses (`/warehouse/`)
- [ ] Can create warehouses

### Admin Dashboard
- [ ] Admin dashboard loads (`/admin/dashboard`)
- [ ] Statistics display correctly
- [ ] Low stock count is accurate
- [ ] Sales sum calculates correctly

### User Dashboard
- [ ] User dashboard loads (`/user/dashboard`)
- [ ] Order history displays
- [ ] Can view order details
- [ ] Can edit profile

## ✅ Database Verification

Run these SQL queries to verify data:

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Check users
SELECT username, role FROM "user";

-- Check products
SELECT product_id, product_name, unit_price FROM product;

-- Check inventory
SELECT inventory_id, product_id, warehouse_id, quantity_available FROM inventory;

-- Check orders
SELECT order_id, customer_id, total_amount, status FROM order_tbl;
```

## ✅ Code Quality

- [ ] No syntax errors
- [ ] All imports work correctly
- [ ] No missing template files
- [ ] All routes are accessible
- [ ] Error handling works

## ✅ Documentation

- [ ] README.md is complete
- [ ] QUICKSTART.md is clear
- [ ] Code comments are present
- [ ] Database schema is documented

## ✅ Final Steps

- [ ] Test all major features end-to-end
- [ ] Verify PostgreSQL connection works
- [ ] Check all forms submit correctly
- [ ] Verify flash messages display
- [ ] Test with multiple users
- [ ] Verify admin vs customer permissions

## 🐛 Common Issues & Fixes

**Issue**: Database connection error
- **Fix**: Check PostgreSQL is running, verify DATABASE_URL format

**Issue**: Module not found
- **Fix**: Activate virtual environment, install requirements

**Issue**: Tables don't exist
- **Fix**: Run `python setup_database.py`

**Issue**: Can't login
- **Fix**: Run `python seed_data.py` to create admin user

**Issue**: Cart is empty after adding items
- **Fix**: Check user is logged in, verify Cart/CartItem relationship

## 📋 Submission Package

Before submitting, ensure you have:

1. ✅ Complete source code
2. ✅ requirements.txt
3. ✅ README.md with setup instructions
4. ✅ Database schema documentation
5. ✅ Screenshots of working features (optional but recommended)
6. ✅ Test data or seed script

## 🎉 Ready to Submit!

If all items above are checked, your project is ready for submission!

Good luck with your college project! 🚀

