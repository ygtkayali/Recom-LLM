#!/usr/bin/env python
"""
Table creation script for SmartBeauty database.

This script creates the main tables (products and concepts) with proper indexing
and vector search capabilities using pgvector extension.

Usage:
    python table_creation.py [--drop-existing] [--create-indexes]
"""

import argparse
import sys
import os
from typing import Optional

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from db.connection import get_database_manager, test_db_connection

# SQL for creating the products table
CREATE_PRODUCTS_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    -- Core Identifier
    id SERIAL PRIMARY KEY,

    -- Essential Display & Searchable Text Fields
    name VARCHAR(255) NOT NULL,
    key_benefits TEXT,
    description TEXT,
    active_content TEXT,
    ingredients_text TEXT, -- A dedicated column for the full ingredient list for allergen filtering
    how_to_use TEXT,

    -- Data for Filtering & Business Logic
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    stock_status INT NOT NULL DEFAULT 0, -- e.g., 0: In Stock, 1: Out of Stock
    is_on_sale BOOLEAN DEFAULT FALSE,
    country VARCHAR(100),

    -- Timestamps for tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    embeddings_text TEXT, -- Concatenated text from keyBenefits, activeContent, name, description, contents, howToUse, timeOfUse for embeddings
    -- The Embedding Vector for Semantic Search
    -- Replace 384 with the dimension of your chosen embedding model.
    embedding VECTOR(384)
);
"""

# SQL for creating the concepts table
CREATE_CONCEPTS_TABLE = """
CREATE TABLE IF NOT EXISTS concepts (
    -- Core Identifier - Matches the IDs in your BeautyPreferences map
    id INT PRIMARY KEY,

    -- Type to distinguish between different kinds of concepts
    concept_type VARCHAR(50) NOT NULL, -- e.g., 'skin_concern', 'skin_type', 'shopping_preference'

    -- Human-readable name and the rich text document for embedding
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL, -- This is the "proxy document" that gets embedded

    -- Timestamps for tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- The Embedding Vector for Semantic Search
    -- MUST be the same dimension as the products.embedding vector.
    embedding VECTOR(384),

    -- Unique constraint to avoid defining the same concept twice
    UNIQUE (concept_type, name)
);
"""

# SQL for creating indexes on products table
CREATE_PRODUCTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);",
    "CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);",
    "CREATE INDEX IF NOT EXISTS idx_products_stock_status ON products (stock_status);",
    "CREATE INDEX IF NOT EXISTS idx_products_country ON products (country);",
    "CREATE INDEX IF NOT EXISTS idx_products_created_at ON products (created_at);",
    # Index for fast text search on the full ingredients list (essential for allergen filtering)
    "CREATE INDEX IF NOT EXISTS idx_products_ingredients_gin ON products USING GIN (to_tsvector('english', ingredients_text));",
    # The CRITICAL index for fast vector similarity search
    # Uses HNSW (Hierarchical Navigable Small World), the state-of-the-art for approximate nearest neighbor search.
    # vector_cosine_ops is often preferred for semantic text similarity.
    "CREATE INDEX IF NOT EXISTS idx_products_embedding_hnsw ON products USING HNSW (embedding vector_cosine_ops);"
]

# SQL for creating indexes on concepts table  
CREATE_CONCEPTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_concepts_type_name ON concepts (concept_type, name);",
    "CREATE INDEX IF NOT EXISTS idx_concepts_type ON concepts (concept_type);",
    "CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts (name);",
    "CREATE INDEX IF NOT EXISTS idx_concepts_created_at ON concepts (created_at);",
    # The CRITICAL index for fast vector similarity search when mapping a query to a concept
    "CREATE INDEX IF NOT EXISTS idx_concepts_embedding_hnsw ON concepts USING HNSW (embedding vector_cosine_ops);"
]

# SQL for dropping tables (if needed)
DROP_PRODUCTS_TABLE = "DROP TABLE IF EXISTS products CASCADE;"
DROP_CONCEPTS_TABLE = "DROP TABLE IF EXISTS concepts CASCADE;"


def create_extension_if_not_exists():
    """Create the pgvector extension if it doesn't exist."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
                print("✅ pgvector extension ensured")
                return True
    except Exception as e:
        print(f"❌ Failed to create pgvector extension: {e}")
        print("Please ensure you have pgvector installed and proper permissions")
        return False


def drop_tables():
    """Drop existing tables."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(DROP_PRODUCTS_TABLE)
                cursor.execute(DROP_CONCEPTS_TABLE)
                conn.commit()
                print("✅ Dropped existing tables")
                return True
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        return False


def create_tables():
    """Create the main tables."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Create products table
                cursor.execute(CREATE_PRODUCTS_TABLE)
                print("✅ Products table created")
                
                # Create concepts table
                cursor.execute(CREATE_CONCEPTS_TABLE)
                print("✅ Concepts table created")
                
                conn.commit()
                return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


def create_indexes():
    """Create indexes for performance optimization."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Create indexes for products table
                for index_sql in CREATE_PRODUCTS_INDEXES:
                    cursor.execute(index_sql)
                    
                # Create indexes for concepts table
                for index_sql in CREATE_CONCEPTS_INDEXES:
                    cursor.execute(index_sql)
                    
                conn.commit()
                print("✅ All indexes created successfully")
                return True
    except Exception as e:
        print(f"❌ Failed to create indexes: {e}")
        return False


def verify_tables():
    """Verify that tables were created successfully."""
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check products table
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'products'
                """)
                if cursor.fetchone()[0] == 1:
                    print("✅ Products table verified")
                else:
                    print("❌ Products table not found")
                    return False
                
                # Check concepts table
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'concepts'
                """)
                if cursor.fetchone()[0] == 1:
                    print("✅ Concepts table verified")
                else:
                    print("❌ Concepts table not found")
                    return False
                
                return True
    except Exception as e:
        print(f"❌ Failed to verify tables: {e}")
        return False


def main():
    """Main function to create database tables."""
    parser = argparse.ArgumentParser(description='Create SmartBeauty database tables')
    parser.add_argument('--drop-existing', action='store_true', 
                       help='Drop existing tables before creating new ones')
    parser.add_argument('--create-indexes', action='store_true', 
                       help='Create performance indexes after tables')
    parser.add_argument('--skip-extension', action='store_true',
                       help='Skip creating pgvector extension')
    
    args = parser.parse_args()
    
    print("🚀 Starting database table creation...")
    
    # Test database connection
    if not test_db_connection():
        print("❌ Database connection failed. Please check your configuration.")
        return False
    
    # Create pgvector extension
    if not args.skip_extension:
        if not create_extension_if_not_exists():
            print("❌ Failed to ensure pgvector extension")
            return False
    
    # Drop existing tables if requested
    if args.drop_existing:
        if not drop_tables():
            print("❌ Failed to drop existing tables")
            return False
    
    # Create tables
    if not create_tables():
        print("❌ Failed to create tables")
        return False
    
    # Create indexes if requested
    if args.create_indexes:
        if not create_indexes():
            print("❌ Failed to create indexes")
            return False
    
    # Verify tables were created
    if not verify_tables():
        print("❌ Table verification failed")
        return False
    
    print("🎉 Database setup completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
