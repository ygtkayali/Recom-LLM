#!/usr/bin/env python
"""
Script to update the embeddings in the products and concepts tables.

This script:
1. Processes entries from both products and concepts tables that don't have embeddings
2. Uses HuggingFace model to create embeddings
3. Updates the database with the embeddings

Usage:
python update_embeddings.py [--batch_size 10] [--table all|products|concepts]

Optional arguments:
--batch_size: Number of items to process at once (default: 10)
--table: Which table to update (default: all)
"""
import os
import sys
import argparse
import psycopg2
import numpy as np

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Import local modules
import rag.core.config as config

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update embeddings in the database.")
    parser.add_argument("--batch_size", type=int, default=10, help="Number of items to process at once")
    parser.add_argument("--table", type=str, default="all", choices=["all", "products", "concepts"],
                        help="Which table to update")
    return parser.parse_args()

def create_embeddings_model():
    """Create and return the embedding model."""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    
    print(f"Loading embedding model: {config.SENTENCE_TRANSFORMER_MODEL_NAME}...")
    return HuggingFaceEmbeddings(
        model_name=config.SENTENCE_TRANSFORMER_MODEL_NAME,
        model_kwargs={'device': 'cpu'}  # Use 'cuda' for GPU if available
    )

def get_products_without_embeddings(conn, batch_size):
    """
    Get products from the database that don't have embeddings.
    
    Args:
        conn: PostgreSQL connection object
        batch_size: Number of products to fetch at once
        
    Returns:
        List of tuples (id, embeddings_text)
    """
    with conn.cursor() as cursor:
        cursor.execute("""
        SELECT id, embeddings_text
        FROM products
        WHERE embedding IS NULL AND embeddings_text IS NOT NULL
        LIMIT %s
        """, (batch_size,))
        return cursor.fetchall()

def get_concepts_without_embeddings(conn, batch_size):
    """
    Get concepts from the database that don't have embeddings.
    
    Args:
        conn: PostgreSQL connection object
        batch_size: Number of concepts to fetch at once
        
    Returns:
        List of tuples (id, description)
    """
    with conn.cursor() as cursor:
        cursor.execute("""
        SELECT id, description
        FROM concepts
        WHERE embedding IS NULL
        LIMIT %s
        """, (batch_size,))
        return cursor.fetchall()

def update_product_embedding(conn, product_id, embedding):
    """
    Update the embedding for a product in the database.
    
    Args:
        conn: PostgreSQL connection object
        product_id: ID of the product to update
        embedding: Vector embedding to store
    """
    with conn.cursor() as cursor:
        # Pass the embedding as is - PostgreSQL will handle the conversion
        cursor.execute("""
        UPDATE products
        SET embedding = %s::vector
        WHERE id = %s
        """, (embedding, product_id))

def update_concept_embedding(conn, concept_id, embedding):
    """
    Update the embedding for a concept in the database.
    
    Args:
        conn: PostgreSQL connection object
        concept_id: ID of the concept to update
        embedding: Vector embedding to store
    """
    with conn.cursor() as cursor:
        # Pass the embedding as is - PostgreSQL will handle the conversion
        cursor.execute("""
        UPDATE concepts
        SET embedding = %s::vector
        WHERE id = %s
        """, (embedding, concept_id))

def update_products(conn, embedding_model, batch_size):
    """
    Update product embeddings in batches.
    
    Args:
        conn: PostgreSQL connection object
        embedding_model: The embedding model to use
        batch_size: Number of products to process at once
        
    Returns:
        Number of products updated
    """
    total_updated = 0
    while True:
        # Get batch of products without embeddings
        products = get_products_without_embeddings(conn, batch_size)
        if not products:
            print("No more products without embeddings.")
            break
        
        print(f"Processing batch of {len(products)} products...")
        for i, (product_id, text) in enumerate(products, 1):
            try:
                # Generate embedding
                embedding = embedding_model.embed_query(text)
                
                # Convert to string format that pgvector can parse
                embedding_str = str(embedding)
                
                # Update the product
                update_product_embedding(conn, product_id, embedding_str)
                total_updated += 1
                print(f"Updated embedding for product {product_id} ({i}/{len(products)} in batch)")
            except Exception as e:
                print(f"Error updating embedding for product {product_id}: {e}")
                conn.rollback()
        
        # Commit after each batch
        conn.commit()
        print(f"Committed batch of {len(products)} products.")
    
    return total_updated

def update_concepts(conn, embedding_model, batch_size):
    """
    Update concept embeddings in batches.
    
    Args:
        conn: PostgreSQL connection object
        embedding_model: The embedding model to use
        batch_size: Number of concepts to process at once
        
    Returns:
        Number of concepts updated
    """
    total_updated = 0
    while True:
        # Get batch of concepts without embeddings
        concepts = get_concepts_without_embeddings(conn, batch_size)
        if not concepts:
            print("No more concepts without embeddings.")
            break
        
        print(f"Processing batch of {len(concepts)} concepts...")
        for i, (concept_id, description) in enumerate(concepts, 1):
            try:
                # Generate embedding
                embedding = embedding_model.embed_query(description)
                
                # Convert to string format that pgvector can parse
                embedding_str = str(embedding)
                
                # Update the concept
                update_concept_embedding(conn, concept_id, embedding_str)
                total_updated += 1
                print(f"Updated embedding for concept {concept_id} ({i}/{len(concepts)} in batch)")
            except Exception as e:
                print(f"Error updating embedding for concept {concept_id}: {e}")
                conn.rollback()
        
        # Commit after each batch
        conn.commit()
        print(f"Committed batch of {len(concepts)} concepts.")
    
    return total_updated

def main():
    """Main function to update embeddings."""
    args = parse_args()
    
    # Import the new connection system
    from db.connection import get_database_manager
    
    # Load embedding model
    embedding_model = create_embeddings_model()
    
    # Connect to PostgreSQL using new connection system
    print("Connecting to PostgreSQL...")
    try:
        products_updated = 0
        concepts_updated = 0
        
        # Update products
        if args.table in ["all", "products"]:
            print("\n--- Processing Products ---")
            with get_database_manager().get_db_connection() as conn:
                products_updated = update_products(conn, embedding_model, args.batch_size)
                print(f"Total products updated with embeddings: {products_updated}")
        
        # Update concepts
        if args.table in ["all", "concepts"]:
            print("\n--- Processing Concepts ---")
            with get_database_manager().get_db_connection() as conn:
                concepts_updated = update_concepts(conn, embedding_model, args.batch_size)
                print(f"Total concepts updated with embeddings: {concepts_updated}")
        
        print("\nDatabase connections closed.")
        print(f"Summary: Updated {products_updated} products and {concepts_updated} concepts.")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()