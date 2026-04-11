# Quick Setup - Fresh PostgreSQL Database

## 🚀 Fast Setup (3 Steps)

### Step 1: Set PostgreSQL Password (if needed)

**PowerShell:**
```powershell
$env:PG_PASSWORD="your_postgres_password"
```

**Or edit the script** and change the default password in `setup_postgresql_simple.py`

### Step 2: Run Setup Script

```bash
python setup_postgresql_simple.py
```

This will:
- ✅ Create database `rims_db`
- ✅ Create all 15 tables
- ✅ Create admin user (admin/admin123)
- ✅ Create sample categories
- ✅ Test all operations

### Step 3: Set DATABASE_URL and Run App

**PowerShell:**
```powershell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/rims_db"
python app.py
```

**CMD:**
```cmd
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rims_db
python app.py
```

## ✅ Verify

```bash
python check_database.py
```

Should show:
```
✓ Using PostgreSQL
✓ Database connection successful!
```

## 🎯 What You Get

- ✅ Fresh PostgreSQL database
- ✅ All 15 tables created
- ✅ Admin user: admin/admin123
- ✅ All operations tested and working
- ✅ Ready to use immediately

## 📝 Custom Configuration

Set environment variables before running:

```powershell
$env:PG_USER="your_username"
$env:PG_PASSWORD="your_password"
$env:PG_HOST="localhost"
$env:PG_PORT="5432"
$env:PG_DB="rims_db"
python setup_postgresql_simple.py
```

## 🎉 Done!

Your database is ready. All data will now save to PostgreSQL!

