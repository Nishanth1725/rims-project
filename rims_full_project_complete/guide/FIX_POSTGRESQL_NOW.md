# 🚨 URGENT: Fix PostgreSQL Connection NOW

## The Problem

Your application is **NOT using PostgreSQL** - it's using SQLite! That's why data isn't showing up in PostgreSQL.

## ✅ IMMEDIATE FIX (3 Steps)

### Step 1: Set DATABASE_URL (REQUIRED!)

**Open PowerShell or CMD in the SAME terminal where you run `python app.py`**

**Windows PowerShell:**
```powershell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/rims_db"
```

**Windows CMD:**
```cmd
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rims_db
```

**Replace:**
- `postgres` = Your PostgreSQL username
- `your_password` = Your PostgreSQL password  
- `rims_db` = Your database name

### Step 2: Verify Connection

```bash
python check_database.py
```

**You MUST see:**
```
✓ Using PostgreSQL
✓ Database connection successful!
```

**If you see "Using SQLite" - DATABASE_URL is NOT set correctly!**

### Step 3: Test Warehouse Save

```bash
python test_warehouse_save.py
```

This will:
- Create a test warehouse
- Save it to database
- Verify it's in PostgreSQL
- Show you exactly what's happening

## 🔍 Verify It's Working

After setting DATABASE_URL and running the app:

1. **Check application startup logs:**
   ```
   ✓ Using PostgreSQL database
   ```

2. **Create a warehouse in the app**

3. **Check PostgreSQL directly:**
   ```sql
   psql -U postgres -d rims_db
   SELECT * FROM warehouse;
   ```

## ⚠️ Common Mistakes

1. **Setting DATABASE_URL in wrong terminal**
   - Must be in SAME terminal as `python app.py`

2. **Wrong connection string format**
   - Must be: `postgresql://user:pass@host:port/db`
   - NOT: `postgresql+psycopg2://...` (we convert it automatically)

3. **Database doesn't exist**
   ```sql
   CREATE DATABASE rims_db;
   ```

4. **Wrong password/username**
   - Verify with: `psql -U postgres`

## 🧪 Quick Test

Run this to see which database you're using:

```bash
python -c "from app import create_app; app = create_app(); print('Database:', app.config['SQLALCHEMY_DATABASE_URI'])"
```

If it shows `sqlite:///rims.db` - DATABASE_URL is NOT set!

## ✅ Success Checklist

- [ ] DATABASE_URL is set in terminal
- [ ] `python check_database.py` shows PostgreSQL
- [ ] `python test_warehouse_save.py` passes
- [ ] Application logs show "Using PostgreSQL"
- [ ] Can see data in PostgreSQL database

## 🆘 Still Not Working?

1. **Check PostgreSQL is running:**
   ```bash
   # Windows - Check Services
   # Look for "postgresql" service
   ```

2. **Test PostgreSQL connection:**
   ```bash
   psql -U postgres -d rims_db
   ```

3. **Check database exists:**
   ```sql
   \l  -- List databases
   ```

4. **Create database if missing:**
   ```sql
   CREATE DATABASE rims_db;
   ```

5. **Run setup:**
   ```bash
   python setup_database.py
   ```

**The code is correct - you just need to set DATABASE_URL!** 🎯

