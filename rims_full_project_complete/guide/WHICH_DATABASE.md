# Which Database is Currently Being Used?

## ⚠️ Current Status: SQLite

**Your system is currently storing data in SQLite, NOT PostgreSQL!**

- **Database Type:** SQLite
- **Database File:** `rims.db` (in your project folder)
- **Reason:** `DATABASE_URL` environment variable is not set

## ✅ To Use PostgreSQL (retail_db)

You need to set the `DATABASE_URL` environment variable **before** starting the application.

### Option 1: Set in PowerShell (Recommended)

```powershell
$env:DATABASE_URL="postgresql://postgres:avinash@localhost:5432/retail_db"
python app.py
```

### Option 2: Set in CMD

```cmd
set DATABASE_URL=postgresql://postgres:avinash@localhost:5432/retail_db
python app.py
```

### Option 3: Use the Helper Scripts

**PowerShell:**
```powershell
.\run_app_with_postgres.ps1
```

**CMD:**
```cmd
run_app_with_postgres.bat
```

## 🔍 How to Check Which Database is Active

Run this command:
```bash
python check_current_database.py
```

Or check the application logs when you start `python app.py`:
- If you see: `⚠️ WARNING: Using SQLite!` → Using SQLite
- If you see: `✓ Using PostgreSQL database` → Using PostgreSQL

## 📊 Database Comparison

| Feature | SQLite (Current) | PostgreSQL (retail_db) |
|---------|------------------|------------------------|
| **Location** | `rims.db` file in project folder | PostgreSQL server (localhost:5432) |
| **Type** | File-based database | Server-based database |
| **Setup** | Automatic (default) | Requires DATABASE_URL |
| **Best For** | Development/Testing | Production/DBMS Projects |

## 🎯 For Your DBMS Project

Since this is a **DBMS project**, you should use **PostgreSQL**:

1. **Set DATABASE_URL** (see above)
2. **Start the application**
3. **Verify** - Check logs for "Using PostgreSQL database"
4. **Test** - Create data and check PostgreSQL:
   ```sql
   psql -U postgres -d retail_db
   SELECT * FROM warehouse;
   SELECT * FROM product;
   ```

## ✅ Quick Switch Command

**PowerShell (one line):**
```powershell
$env:DATABASE_URL="postgresql://postgres:avinash@localhost:5432/retail_db"; python app.py
```

**CMD (one line):**
```cmd
set DATABASE_URL=postgresql://postgres:avinash@localhost:5432/retail_db && python app.py
```

## 📝 Important Notes

- **SQLite** stores data in a file (`rims.db`)
- **PostgreSQL** stores data in the `retail_db` database on the PostgreSQL server
- **You must set DATABASE_URL** before starting the app to use PostgreSQL
- **The environment variable** only lasts for that terminal session
- **To make it permanent**, you can add it to your system environment variables

