"""
Migration script to add missing Product model fields to PostgreSQL database.

This script adds the following columns to the 'product' table:
- online_payment_enabled (BOOLEAN, default False)
- cod_enabled (BOOLEAN, default True)
- qr_code_filename (VARCHAR(255), nullable)
- delivery_days (INTEGER, default 3)

The script safely checks if columns exist before adding them and can be run multiple times safely.
"""

import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import ProgrammingError

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db


def column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_product_table():
    """Add missing columns to the product table."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get the database engine
            engine = db.engine
            
            # Check if the product table exists
            inspector = inspect(engine)
            if 'product' not in inspector.get_table_names():
                print("ERROR: 'product' table does not exist. Please run db.create_all() first.")
                return False
            
            print("=" * 60)
            print("MIGRATING PRODUCT TABLE")
            print("=" * 60)
            
            # List of columns to add with their definitions
            # Note: PostgreSQL BOOLEAN defaults should be TRUE/FALSE (not strings)
            columns_to_add = [
                {
                    'name': 'online_payment_enabled',
                    'sql_type': 'BOOLEAN',
                    'default': False,  # Boolean value, not string
                    'default_sql': 'FALSE',
                    'nullable': False
                },
                {
                    'name': 'cod_enabled',
                    'sql_type': 'BOOLEAN',
                    'default': True,  # Boolean value, not string
                    'default_sql': 'TRUE',
                    'nullable': False
                },
                {
                    'name': 'qr_code_filename',
                    'sql_type': 'VARCHAR(255)',
                    'default': None,
                    'default_sql': None,
                    'nullable': True
                },
                {
                    'name': 'delivery_days',
                    'sql_type': 'INTEGER',
                    'default': 3,  # Integer value
                    'default_sql': '3',
                    'nullable': False
                }
            ]
            
            # Check and add each column
            for col_def in columns_to_add:
                col_name = col_def['name']
                
                if column_exists(engine, 'product', col_name):
                    print(f"[SKIP] Column '{col_name}' already exists. Skipping...")
                else:
                    try:
                        # For PostgreSQL, add column with proper defaults
                        default_sql = col_def.get('default_sql', col_def.get('default'))
                        
                        if default_sql is not None and not col_def['nullable']:
                            # Try simple approach first (PostgreSQL 9.1+ supports this)
                            try:
                                alter_sql = f'ALTER TABLE product ADD COLUMN {col_name} {col_def["sql_type"]} NOT NULL DEFAULT {default_sql}'
                                db.session.execute(text(alter_sql))
                                db.session.commit()
                                print(f"[OK] Added column '{col_name}' (NOT NULL, DEFAULT {default_sql}) successfully")
                            except ProgrammingError as pe:
                                # Fallback for older PostgreSQL versions: multi-step approach
                                error_msg = str(pe).lower()
                                if 'violates not-null constraint' in error_msg or 'not-null constraint' in error_msg:
                                    db.session.rollback()
                                    print(f"  Using multi-step approach for '{col_name}'...")
                                    # Step 1: Add as nullable
                                    alter_sql_step1 = f'ALTER TABLE product ADD COLUMN {col_name} {col_def["sql_type"]}'
                                    db.session.execute(text(alter_sql_step1))
                                    db.session.commit()
                                    # Step 2: Update existing rows
                                    update_sql = f'UPDATE product SET {col_name} = {default_sql} WHERE {col_name} IS NULL'
                                    db.session.execute(text(update_sql))
                                    db.session.commit()
                                    # Step 3: Set NOT NULL and DEFAULT
                                    alter_sql_step3 = f'ALTER TABLE product ALTER COLUMN {col_name} SET NOT NULL, ALTER COLUMN {col_name} SET DEFAULT {default_sql}'
                                    db.session.execute(text(alter_sql_step3))
                                    db.session.commit()
                                    print(f"[OK] Added column '{col_name}' (NOT NULL, DEFAULT {default_sql}) using multi-step approach")
                                else:
                                    raise
                            
                        elif default_sql is not None and col_def['nullable']:
                            # Nullable column with default
                            alter_sql = f'ALTER TABLE product ADD COLUMN {col_name} {col_def["sql_type"]} DEFAULT {default_sql}'
                            db.session.execute(text(alter_sql))
                            db.session.commit()
                            print(f"[OK] Added column '{col_name}' (NULLABLE, DEFAULT {default_sql}) successfully")
                        else:
                            # Nullable column without default
                            alter_sql = f'ALTER TABLE product ADD COLUMN {col_name} {col_def["sql_type"]}'
                            db.session.execute(text(alter_sql))
                            db.session.commit()
                            print(f"[OK] Added column '{col_name}' (NULLABLE) successfully")
                        
                    except ProgrammingError as e:
                        db.session.rollback()
                        error_msg = str(e)
                        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                            print(f"[SKIP] Column '{col_name}' already exists (detected by database). Skipping...")
                        else:
                            print(f"[ERROR] Error adding column '{col_name}': {error_msg}")
                            return False
                    except Exception as e:
                        db.session.rollback()
                        print(f"[ERROR] Unexpected error adding column '{col_name}': {str(e)}")
                        return False
            
            # Verify all columns were added
            print("\n" + "=" * 60)
            print("VERIFICATION")
            print("=" * 60)
            
            inspector = inspect(engine)
            product_columns = [col['name'] for col in inspector.get_columns('product')]
            
            all_added = True
            for col_def in columns_to_add:
                col_name = col_def['name']
                if col_name in product_columns:
                    print(f"[OK] Verified: '{col_name}' exists in product table")
                else:
                    print(f"[ERROR] '{col_name}' is missing from product table")
                    all_added = False
            
            if all_added:
                print("\n" + "=" * 60)
                print("MIGRATION COMPLETED SUCCESSFULLY")
                print("=" * 60)
                return True
            else:
                print("\n" + "=" * 60)
                print("MIGRATION COMPLETED WITH ERRORS")
                print("=" * 60)
                return False
                
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] FATAL ERROR during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    # Fix Windows console encoding issue
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("\nStarting Product table migration...\n")
    success = migrate_product_table()
    
    if success:
        print("\n[SUCCESS] Migration script completed successfully!")
        print("You can now create and edit products without errors.\n")
        sys.exit(0)
    else:
        print("\n[FAILED] Migration script encountered errors.")
        print("Please review the error messages above and try again.\n")
        sys.exit(1)

