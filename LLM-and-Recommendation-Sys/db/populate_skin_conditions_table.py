#!/usr/bin/env python
"""
Script to populate the skin_conditions table in PostgreSQL with data from class_descriptions.py.
This script creates entries with id (auto-generated), name, description, and embedding_vector columns.

Table schema:
- id: Primary key (serial) - Auto-generated sequence
- name: Condition name (text) - From SKIN_CONDITION_PROFILES keys
- description: Full text description (text) - From SKIN_CONDITION_PROFILES values
- embedding_vector: Vector data (vector) - To be filled later by update_embeddings.py

Usage:
python populate_skin_conditions_table.py

The script reads configuration from config.py and skin condition data from class_descriptions.py.
"""
import os
import sys
import psycopg2

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, parent_dir)

# Import local modules
import rag.core.config as config
from rag.core.class_descriptions import SKIN_CONDITION_PROFILES

def create_skin_conditions_table(conn):
    """
    Create the skin_conditions table if it doesn't exist.
    
    Args:
        conn: PostgreSQL connection object
    """
    with conn.cursor() as cursor:
        # Create the simplified skin_conditions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skin_conditions (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL
        );
        """)
        conn.commit()
        print("Skin conditions table created or already exists.")

def insert_skin_condition(cursor, name, description):
    """
    Insert a skin condition into the skin_conditions table.
    
    Args:
        cursor: PostgreSQL cursor
        name: Name of the skin condition
        description: Description of the skin condition
    """
    # Insert the skin condition
    cursor.execute("""
    INSERT INTO skin_conditions (name, description)
    VALUES (%s, %s)
    ON CONFLICT (name) DO UPDATE 
    SET description = EXCLUDED.description;
    """, (name, description))

def populate_skin_conditions_table(conn, skin_conditions):
    """
    Populate the skin_conditions table with the provided dictionary of skin conditions.
    
    Args:
        conn: PostgreSQL connection object
        skin_conditions: Dictionary mapping condition names to descriptions
    """
    with conn.cursor() as cursor:
        for i, (name, description) in enumerate(skin_conditions.items(), 1):
            try:
                # Clean up the description text (remove extra whitespace)
                clean_description = description.strip()
                
                insert_skin_condition(cursor, name, clean_description)
                print(f"Processed skin condition {i}/{len(skin_conditions)}: {name}")
            except Exception as e:
                print(f"Error inserting skin condition {name}: {e}")
                conn.rollback()
    
    conn.commit()
    print("Skin conditions table population complete.")

def count_skin_conditions_in_table(conn):
    """
    Count the number of skin conditions in the skin_conditions table.
    
    Args:
        conn: PostgreSQL connection object
        
    Returns:
        Number of skin conditions in the table
    """
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM skin_conditions")
        count = cursor.fetchone()[0]
        return count

def main():
    """Main function to populate the skin_conditions table."""
    # Import the utilities for database connection
    from utils import create_db_connection_from_config
    
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    try:
        conn = create_db_connection_from_config()
        if not conn:
            print("Failed to connect to database")
            return
        
        print("Connected to PostgreSQL. Creating table if it doesn't exist...")
        create_skin_conditions_table(conn)
        
        # Count existing skin conditions
        initial_count = count_skin_conditions_in_table(conn)
        print(f"Current skin condition count in database: {initial_count}")
        
        # Populate the table
        print(f"Populating skin_conditions table with {len(SKIN_CONDITION_PROFILES)} entries...")
        populate_skin_conditions_table(conn, SKIN_CONDITION_PROFILES)
        
        # Count after insertion
        final_count = count_skin_conditions_in_table(conn)
        print(f"Final skin condition count in database: {final_count}")
        print(f"Added {final_count - initial_count} new skin conditions.")
        
        conn.close()
        print("Database connection closed.")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
