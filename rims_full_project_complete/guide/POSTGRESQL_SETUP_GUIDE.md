# PostgreSQL Setup Guide - Fix Database Connection

## ⚠️ Problem: Data Not Saving to PostgreSQL

**Issue:** The application is using SQLite instead of PostgreSQL because `DATABASE_URL` environment variable is not set.

## ✅ Solution: Set DATABASE_URL Environment Variable

### Step 1: Check Current Database

Run this command to see which database is being used:
```bash
python check_database.py
```

### Step 2: Set DATABASE_URL

**Windows PowerShell:**
```powershell
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/rims_db"
```

**Windows CMD:**
```cmd
set DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rims_db
```

**Linux/Mac:**
```bash
export DATABASE_URL="postgresql://postgres:your_password@localhost:5432/rims_db"
```

**Replace:**
- `postgres` with your PostgreSQL username
- `your_password` with your PostgreSQL password
- `rims_db` with your database name

### Step 3: Verify Connection

```bash
python check_database.py
```

You should see:
```
✓ Using PostgreSQL
✓ Database connection successful!
✓ 'warehouse' table exists
```

### Step 4: Create Database (if not exists)

Connect to PostgreSQL:
```bash
psql -U postgres
```

Then run:
```sql
CREATE DATABASE rims_db;
```

Or if using a different user:
```sql
CREATE DATABASE rims_db;
CREATE USER rims_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE rims_db TO rims_user;
```

### Step 5: Initialize Tables

```bash
python setup_database.py
```

### Step 6: Test Warehouse Creation

1. Start the application:
   ```bash
   python app.py
   ```

2. Login as admin
3. Go to `/warehouse/create`
4. Create a warehouse
5. Check PostgreSQL:
   ```sql
   SELECT * FROM warehouse;
   ```

## 🔍 Permanent Solution (Optional)

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rims_db
SECRET_KEY=your-secret-key-here
```

Then install python-dotenv:
```bash
pip install python-dotenv
```

And update `config.py` to load from .env file.

## ✅ Verification Checklist

- [ ] PostgreSQL is running
- [ ] Database `rims_db` exists
- [ ] DATABASE_URL environment variable is set
- [ ] `python check_database.py` shows PostgreSQL
- [ ] Tables are created (`python setup_database.py`)
- [ ] Can create warehouse and see it in PostgreSQL

## 🐛 Troubleshooting

**Still using SQLite?**
- Make sure DATABASE_URL is set in the SAME terminal where you run `python app.py`
- Restart the application after setting DATABASE_URL
- Check: `python check_database.py` should show PostgreSQL

**Connection refused?**
- Check PostgreSQL is running
- Verify username, password, host, port
- Check firewall settings

**Permission denied?**
- Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE rims_db TO your_user;`

