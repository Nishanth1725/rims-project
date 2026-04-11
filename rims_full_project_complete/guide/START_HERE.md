# 🚨 START HERE - Fix PostgreSQL Connection

## The Problem

Your data is NOT saving to PostgreSQL because the app is using SQLite!

## ✅ QUICK FIX (Choose ONE method)

### Method 1: Run Setup Script (EASIEST)

**Windows PowerShell:**
```powershell
.\set_postgresql.ps1
```

**Windows CMD:**
```cmd
set_postgresql.bat
```

This will ask for your PostgreSQL details and set DATABASE_URL automatically.

### Method 2: Manual Setup

**Open PowerShell or CMD and run:**

```powershell
# PowerShell
$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/rims_db"
```

```cmd
# CMD
set DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/rims_db
```

**Replace `YOUR_PASSWORD` with your actual PostgreSQL password!**

## ✅ Verify It's Working

**Step 1: Check Database**
```bash
python check_database.py
```

**You MUST see:**
```
✓ Using PostgreSQL
✓ Database connection successful!
```

**If you see "Using SQLite" - DATABASE_URL is NOT set!**

**Step 2: Test Save**
```bash
python test_warehouse_save.py
```

This will create a test warehouse and verify it saves to PostgreSQL.

**Step 3: Start Application**
```bash
python app.py
```

**Check the startup logs - you should see:**
```
✓ Using PostgreSQL database
```

## ⚠️ IMPORTANT

1. **Set DATABASE_URL in the SAME terminal** where you run `python app.py`
2. **Keep that terminal open** - environment variables reset when terminal closes
3. **Restart the app** after setting DATABASE_URL

## 🧪 Quick Test

After setting DATABASE_URL:

1. Create a warehouse in the app
2. Check PostgreSQL:
   ```sql
   psql -U postgres -d rims_db
   SELECT * FROM warehouse;
   ```

You should see your warehouse!

## 📋 Checklist

- [ ] Ran setup script OR set DATABASE_URL manually
- [ ] `python check_database.py` shows PostgreSQL
- [ ] `python test_warehouse_save.py` passes
- [ ] Application logs show "Using PostgreSQL"
- [ ] Can create warehouse and see it in PostgreSQL

## 🆘 Still Not Working?

1. **Check PostgreSQL is running**
2. **Verify database exists:**
   ```sql
   CREATE DATABASE rims_db;
   ```
3. **Run setup:**
   ```bash
   python setup_database.py
   ```

**The code is correct - you just need to set DATABASE_URL!** 🎯

