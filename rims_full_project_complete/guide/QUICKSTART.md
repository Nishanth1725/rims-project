# Quick Start Guide - RIMS

## Fast Setup (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up PostgreSQL Database

**Option A: Create database manually**
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE rims_db;

-- (Optional) Create user
CREATE USER rims_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE rims_db TO rims_user;
```

**Option B: Use environment variable**
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/rims_db"

# Windows CMD
set DATABASE_URL=postgresql://postgres:password@localhost:5432/rims_db

# Linux/Mac
export DATABASE_URL="postgresql://postgres:password@localhost:5432/rims_db"
```

### Step 3: Initialize Database
```bash
python setup_database.py
```

### Step 4: Seed Sample Data
```bash
python seed_data.py
```

### Step 5: Run Application
```bash
python app.py
```

### Step 6: Access the Application
- Open browser: `http://localhost:5000`
- Admin login: `admin` / `admin123`
- Register a new customer account

## Troubleshooting

**Database connection error?**
- Check PostgreSQL is running
- Verify DATABASE_URL format: `postgresql://user:pass@host:port/db`
- Ensure database exists

**Module not found?**
- Activate virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
- Install dependencies: `pip install -r requirements.txt`

**Tables not created?**
- Run `python setup_database.py` manually
- Check database user has CREATE privileges

## Default Credentials

After seeding:
- **Admin**: username=`admin`, password=`admin123`

## Key Features

✅ User registration and authentication
✅ Product catalog and management
✅ Shopping cart functionality
✅ Order processing
✅ Inventory management
✅ Warehouse management
✅ Admin dashboard with statistics
✅ User dashboard with order history

## Next Steps

1. Log in as admin
2. Add products via `/product/create`
3. Create warehouses via `/warehouse/create`
4. Add inventory via `/inventory/add`
5. Register as customer and start shopping!

