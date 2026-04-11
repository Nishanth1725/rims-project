# Complete Database Setup - Fresh PostgreSQL Database

## 🎯 What This Does

This script creates a **completely fresh PostgreSQL database** with:
- ✅ All 15 tables created
- ✅ Proper relationships and foreign keys
- ✅ Test data verification
- ✅ Admin user created
- ✅ Everything verified and working

## 🚀 Quick Start

### Step 1: Run Setup Script

```bash
python create_fresh_database.py
```

The script will:
1. Ask for PostgreSQL connection details
2. Create the database (or use existing)
3. Create ALL tables from scratch
4. Verify everything works
5. Create admin user
6. Test all operations

### Step 2: Set DATABASE_URL

After the script completes, it will show you the connection string.

**Copy and run this in your terminal:**

**PowerShell:**
```powershell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/rims_db"
```

**CMD:**
```cmd
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rims_db
```

### Step 3: Verify

```bash
python check_database.py
```

Should show:
```
✓ Using PostgreSQL
✓ Database connection successful!
✓ 'warehouse' table exists
```

### Step 4: Start Application

```bash
python app.py
```

### Step 5: Login

- **URL:** http://localhost:5000
- **Username:** admin
- **Password:** admin123

## 📊 What Gets Created

### Tables Created (15 total):

1. ✅ `user` - User accounts
2. ✅ `category` - Product categories
3. ✅ `product` - Products
4. ✅ `warehouse` - Warehouses
5. ✅ `inventory` - Inventory per warehouse
6. ✅ `cart` - Shopping carts
7. ✅ `cart_item` - Cart items
8. ✅ `order_tbl` - Orders
9. ✅ `order_detail` - Order line items
10. ✅ `payment` - Payment records
11. ✅ `provider` - Suppliers
12. ✅ `customer` - Customer information
13. ✅ `delivery` - Delivery records
14. ✅ `delivery_detail` - Delivery line items
15. ✅ `transfer` - Warehouse transfers

### Initial Data:

- ✅ Admin user (admin/admin123)
- ✅ Sample category (Electronics)

## ✅ Verification Tests

The script automatically tests:

1. ✅ Database connection
2. ✅ Table structure (all columns)
3. ✅ INSERT operation (create warehouse)
4. ✅ SELECT operation (query warehouse)
5. ✅ UPDATE operation (update warehouse)
6. ✅ DELETE operation (delete warehouse)
7. ✅ User creation
8. ✅ Category creation

**All tests must pass for setup to complete!**

## 🔍 Verify in PostgreSQL

After setup, check in PostgreSQL:

```sql
-- Connect to database
psql -U postgres -d rims_db

-- List all tables
\dt

-- Check warehouse table
SELECT * FROM warehouse;

-- Check user table
SELECT username, role FROM "user";

-- Check all tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

## 🎯 What This Fixes

**Before:**
- ❌ Using SQLite instead of PostgreSQL
- ❌ Data not saving to PostgreSQL
- ❌ Tables might not exist
- ❌ No verification

**After:**
- ✅ Fresh PostgreSQL database
- ✅ All tables created correctly
- ✅ All operations tested and verified
- ✅ Ready to use immediately

## 📝 Important Notes

1. **The script will DROP existing tables** if you choose to recreate
2. **Backup your data** if you have important data
3. **Set DATABASE_URL** in the same terminal where you run the app
4. **Keep terminal open** - environment variables reset when closed

## 🆘 Troubleshooting

**"Database already exists"**
- Script will ask if you want to drop and recreate
- Choose 'y' for fresh start, 'n' to use existing

**"Connection failed"**
- Check PostgreSQL is running
- Verify username/password
- Check host/port

**"Tables not created"**
- Check database user has CREATE privileges
- Run script again

**"Still using SQLite"**
- Make sure DATABASE_URL is set
- Restart application after setting DATABASE_URL

## ✅ Success Indicators

After running the script, you should see:

```
✅ ALL TESTS PASSED - Database is ready!
✅ DATABASE SETUP COMPLETE!
```

Then when you run the app:
- Logs show "Using PostgreSQL database"
- Can create warehouses and see them in PostgreSQL
- All CRUD operations work

**Your database is now ready for your DBMS project!** 🎉

