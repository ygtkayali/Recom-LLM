#!/usr/bin/env python
"""
Quick verification script to check if product IDs from JSON are being used.
"""
import os
import sys

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from db.connection import get_database_manager

def verify_product_ids():
    """Check if the products in the database use the original IDs from JSON."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT id, name FROM products ORDER BY id LIMIT 10')
                rows = cursor.fetchall()
                print('First 10 products with their IDs:')
                print('-' * 50)
                for row in rows:
                    print(f'ID: {row[0]:3d}, Name: {row[1]}')
                
                # Check if IDs match expected pattern (103, 104, etc. from JSON)
                cursor.execute('SELECT MIN(id), MAX(id), COUNT(*) FROM products')
                min_id, max_id, count = cursor.fetchone()
                print(f'\nID Statistics:')
                print(f'Minimum ID: {min_id}')
                print(f'Maximum ID: {max_id}')
                print(f'Total products: {count}')
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_product_ids()
