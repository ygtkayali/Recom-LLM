#!/usr/bin/env python
"""
Script to check the status of the database tables.

This script:
1. Connects to the PostgreSQL database
2. Checks if the tables exist
3. Counts rows with and without embeddings
4. Shows sample entries

Usage:
python check_database_tables.py
"""
import os
import sys
import psycopg2

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Import local modules
import rag.core.config as config

def check_table_exists(conn, table_name):
    """
    Check if a table exists in the database.
    
    Args:
        conn: PostgreSQL connection object
        table_name: Name of the table to check
        
    Returns:
        True if the table exists, False otherwise
    """
    with conn.cursor() as cursor:
        cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
        """, (table_name,))
        return cursor.fetchone()[0]

def check_products_table(conn):
    """
    Check the status of the products table.
    
    Args:
        conn: PostgreSQL connection object
    """
    table_name = "products"
    if not check_table_exists(conn, table_name):
        print(f"❌ {table_name.capitalize()} table does not exist.")
        return
    
    print(f"✅ {table_name.capitalize()} table exists.")
    
    with conn.cursor() as cursor:
        # Count total rows
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        print(f"Total products: {total_count}")
        
        # Count rows with embeddings
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding_vector IS NOT NULL")
        with_embeddings = cursor.fetchone()[0]
        print(f"Products with embeddings: {with_embeddings}")
        
        # Count rows without embeddings
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding_vector IS NULL")
        without_embeddings = cursor.fetchone()[0]
        print(f"Products without embeddings: {without_embeddings}")
        
        # Get a sample
        if total_count > 0:
            cursor.execute(f"""
            SELECT id, name, embedding_text_concatenated, embedding_vector IS NOT NULL
            FROM {table_name}
            LIMIT 1
            """)
            sample = cursor.fetchone()
            if sample:
                product_id, name, text, has_embedding = sample
                print(f"Sample product:")
                print(f"ID: {product_id}")
                print(f"Name: {name}")
                print(f"Text snippet: {text[:100]}..." if text and len(text) > 100 else f"Text: {text}")
                print(f"Has embedding: {'Yes' if has_embedding else 'No'}")

def check_skin_conditions_table(conn):
    """
    Check the status of the skin_conditions table.
    
    Args:
        conn: PostgreSQL connection object
    """
    table_name = "skin_conditions"
    if not check_table_exists(conn, table_name):
        print(f"❌ {table_name.replace('_', ' ').title()} table does not exist.")
        return
    
    print(f"✅ {table_name.replace('_', ' ').title()} table exists.")
    
    with conn.cursor() as cursor:
        # Count total rows
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        print(f"Total skin conditions: {total_count}")
        
        # Count rows with embeddings
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding_vector IS NOT NULL")
        with_embeddings = cursor.fetchone()[0]
        print(f"Skin conditions with embeddings: {with_embeddings}")
        
        # Count rows without embeddings
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding_vector IS NULL")
        without_embeddings = cursor.fetchone()[0]
        print(f"Skin conditions without embeddings: {without_embeddings}")
        
        # Get a sample
        if total_count > 0:
            cursor.execute(f"""
            SELECT id, name, description, embedding_vector IS NOT NULL
            FROM {table_name}
            LIMIT 1
            """)
            sample = cursor.fetchone()
            if sample:
                condition_id, name, description, has_embedding = sample
                print(f"Sample skin condition:")
                print(f"ID: {condition_id}")
                print(f"Name: {name}")
                print(f"Description snippet: {description[:100]}..." if description and len(description) > 100 else f"Description: {description}")
                print(f"Has embedding: {'Yes' if has_embedding else 'No'}")

def main():
    """Main function to check database tables."""
    # Import the utilities for database connection
    from utils import create_db_connection_from_config
    
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    try:
        conn = create_db_connection_from_config()
        if not conn:
            print("Failed to connect to database")
            return
        
        print("\n--- Products Table ---")
        check_products_table(conn)
        
        print("\n--- Skin Conditions Table ---")
        check_skin_conditions_table(conn)
        
        conn.close()
        print("\nDatabase connection closed.")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
