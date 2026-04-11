# Retail Inventory Management System (RIMS)

A comprehensive retail inventory management system built with Flask and PostgreSQL.

## Features

- **User Management**: Customer registration, login, and admin authentication
- **Product Management**: Create, edit, delete products with categories and images
- **Inventory Management**: Track inventory across multiple warehouses with reorder points
- **Shopping Cart**: Add products to cart, update quantities, checkout
- **Order Management**: Create orders, track order status, view order history
- **Payment Processing**: Mock payment system with receipts
- **Warehouse Management**: Manage multiple warehouses with capacity tracking
- **Provider Management**: Track suppliers and providers
- **Transfer Management**: Transfer products between warehouses
- **Delivery Management**: Track deliveries and delivery details
- **Admin Dashboard**: View sales statistics, low stock alerts, product counts
- **User Dashboard**: View orders, edit profile, manage addresses

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

## Installation

### 1. Clone or navigate to the project directory

```bash
cd rims_full_project_complete
```

### 2. Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL Database

#### Option A: Using existing PostgreSQL server

1. Create a new database:
```sql
CREATE DATABASE rims_db;
```

2. Create a user (optional):
```sql
CREATE USER rims_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE rims_db TO rims_user;
```

#### Option B: Using environment variables

Set the `DATABASE_URL` environment variable:

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL="postgresql://username:password@localhost:5432/rims_db"
```

**Windows (CMD):**
```cmd
set DATABASE_URL=postgresql://username:password@localhost:5432/rims_db
```

**Linux/Mac:**
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/rims_db"
```

**Format:** `postgresql://username:password@host:port/database_name`

#### Option C: Using .env file (recommended)

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/rims_db
SECRET_KEY=your-secret-key-here
```

### 5. Set Secret Key (optional)

If not using .env file, set the `SECRET_KEY` environment variable:

**Windows:**
```powershell
$env:SECRET_KEY="your-secret-key-here"
```

**Linux/Mac:**
```bash
export SECRET_KEY="your-secret-key-here"
```

### 6. Initialize the database

The database tables will be created automatically when you run the application for the first time.

### 7. Seed sample data (optional)

```bash
python seed_data.py
```

This will create:
- Sample categories (Electronics, Home Appliances)
- Sample products
- A main warehouse
- Inventory entries
- Admin user (username: `admin`, password: `admin123`)

## Running the Application

### Start the Flask development server

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Default Routes

- **Home**: `http://localhost:5000/`
- **Registration**: `http://localhost:5000/auth/register`
- **Login**: `http://localhost:5000/auth/login`
- **Admin Login**: `http://localhost:5000/auth/login_admin`
- **Catalog**: `http://localhost:5000/catalog/`
- **Admin Dashboard**: `http://localhost:5000/admin/dashboard`
- **User Dashboard**: `http://localhost:5000/user/dashboard`

## Default Admin Credentials

After running `seed_data.py`:
- **Username**: `admin`
- **Password**: `admin123`

## Project Structure

```
rims_full_project_complete/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── extensions.py          # Flask extensions (db, login_manager)
├── models.py              # SQLAlchemy database models
├── seed_data.py           # Database seeding script
├── requirements.txt       # Python dependencies
├── blueprints/            # Flask blueprints (route modules)
│   ├── auth.py            # Authentication routes
│   ├── catalog.py         # Product catalog
│   ├── product.py         # Product management
│   ├── cart.py            # Shopping cart
│   ├── payment.py         # Payment processing
│   ├── order.py           # Order management
│   ├── inventory.py       # Inventory management
│   ├── warehouse.py       # Warehouse management
│   ├── provider.py        # Provider management
│   ├── transfer.py        # Warehouse transfers
│   ├── delivery.py        # Delivery management
│   ├── admin_dashboard.py # Admin dashboard
│   └── user_dashboard.py  # User dashboard
├── templates/             # Jinja2 HTML templates
├── static/               # Static files (CSS, JS, images)
│   └── uploads/          # Product image uploads
└── instance/             # Instance folder (SQLite DB if used)
```

## Database Models

- **User**: User accounts (customers and admins)
- **Category**: Product categories
- **Product**: Products with prices, descriptions, images
- **Warehouse**: Warehouse locations with capacity
- **Inventory**: Product inventory per warehouse with reorder points
- **Cart**: Shopping carts (user or session-based)
- **CartItem**: Items in shopping carts
- **Order**: Customer orders
- **OrderDetail**: Order line items
- **Payment**: Payment records
- **Provider**: Suppliers/providers
- **Customer**: Customer information
- **Delivery**: Delivery records
- **DeliveryDetail**: Delivery line items
- **Transfer**: Warehouse transfer records

## Troubleshooting

### Database Connection Issues

1. **Check PostgreSQL is running:**
   ```bash
   # Windows
   # Check Services for PostgreSQL
   
   # Linux/Mac
   sudo systemctl status postgresql
   ```

2. **Verify connection string format:**
   - Format: `postgresql://username:password@host:port/database`
   - Default port: `5432`

3. **Check database exists:**
   ```sql
   \l  -- List databases in psql
   ```

4. **Check user permissions:**
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE rims_db TO your_user;
   ```

### Common Errors

- **"Module not found"**: Make sure virtual environment is activated and dependencies are installed
- **"Database connection refused"**: Check PostgreSQL is running and connection string is correct
- **"Table does not exist"**: Run the application once to create tables, or run migrations
- **"Permission denied"**: Check database user has proper permissions

## Development Notes

- The application uses Flask-SQLAlchemy for ORM
- CSRF protection is enabled via Flask-WTF
- User authentication uses Flask-Login
- Product images are stored in `static/uploads/`
- The system supports both authenticated users and guest sessions

## Production Deployment

For production:
1. Set a strong `SECRET_KEY`
2. Use a production-grade PostgreSQL server
3. Configure proper database connection pooling
4. Set up proper file upload handling
5. Use a production WSGI server (e.g., Gunicorn)
6. Configure reverse proxy (e.g., Nginx)
7. Enable HTTPS
8. Set up proper logging and monitoring

## License

This project is for educational purposes.

## Support

For issues or questions, please check the code comments or database schema in `models.py`.
