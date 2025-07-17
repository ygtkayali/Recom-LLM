#!/usr/bin/env python
"""
Test script to demonstrate the get_related_skin_conditions_for_product function.

This script:
1. Shows how to find related skin conditions for a given product ID
2. Shows how to find related products for a given skin condition ID
3. Uses embedding similarity to make these connections

Usage:
python test_product_skin_condition_similarity.py [--product_id 123] [--condition_id 456]
"""
import os
import sys
import argparse

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Import local modules
from utils import get_related_skin_conditions_for_product, get_products_for_skin_condition

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test product-skin condition similarity functions")
    parser.add_argument("--product_id", type=int, help="Product ID to find related skin conditions for")
    parser.add_argument("--condition_id", type=int, help="Skin condition ID to find related products for")
    parser.add_argument("--top_n", type=int, default=5, help="Number of top results to return (default: 5)")
    parser.add_argument("--similarity_threshold", type=float, default=0.6, help="Minimum similarity threshold (default: 0.6)")
    return parser.parse_args()

def test_product_to_conditions(product_id, top_n, similarity_threshold):
    """Test finding skin conditions related to a product."""
    print(f"\n🔍 Finding skin conditions related to product ID {product_id}")
    print("="*60)
    
    results = get_related_skin_conditions_for_product(
        product_id=product_id,
        top_n=top_n,
        similarity_threshold=similarity_threshold
    )
    
    if not results:
        print(f"No related skin conditions found for product ID {product_id}")
        return
    
    print(f"\nFound {len(results)} related skin conditions:")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['condition_name']} (ID: {result['condition_id']})")
        print(f"   Similarity: {result['similarity']:.4f}")
        print(f"   Description: {result['condition_description']}")
        print(f"   Related to product: {result['product_name']}")
        print("-" * 60)

def test_condition_to_products(condition_id, top_n, similarity_threshold):
    """Test finding products related to a skin condition."""
    print(f"\n🔍 Finding products related to skin condition ID {condition_id}")
    print("="*60)
    
    results = get_products_for_skin_condition(
        condition_id=condition_id,
        top_n=top_n,
        similarity_threshold=similarity_threshold
    )
    
    if not results:
        print(f"No related products found for skin condition ID {condition_id}")
        return
    
    print(f"\nFound {len(results)} related products:")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['product_name']} (ID: {result['product_id']})")
        print(f"   Similarity: {result['similarity']:.4f}")
        print(f"   Key Benefits: {result['key_benefits']}")
        print(f"   Related to condition: {result['condition_name']}")
        print("-" * 60)

def show_sample_data():
    """Show some sample product and skin condition IDs for testing."""
    from utils import create_db_connection_from_config
    
    print("\n📋 Sample data for testing:")
    print("="*40)
    
    conn = create_db_connection_from_config()
    if not conn:
        print("Could not connect to database to show sample data")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get some sample products
        print("\nSample Products (with embeddings):")
        cursor.execute("""
        SELECT id, name FROM products 
        WHERE embedding_vector IS NOT NULL 
        LIMIT 5
        """)
        
        for row in cursor.fetchall():
            product_id, name = row
            print(f"  - ID {product_id}: {name}")
        
        # Get some sample skin conditions
        print("\nSample Skin Conditions (with embeddings):")
        cursor.execute("""
        SELECT id, name FROM skin_conditions 
        WHERE embedding_vector IS NOT NULL 
        LIMIT 5
        """)
        
        for row in cursor.fetchall():
            condition_id, name = row
            print(f"  - ID {condition_id}: {name}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error retrieving sample data: {e}")
        if conn:
            conn.close()

def main():
    """Main function."""
    args = parse_args()
    
    # If no specific IDs provided, show sample data
    if not args.product_id and not args.condition_id:
        print("No specific product or condition ID provided.")
        show_sample_data()
        print("\nTo test the similarity functions, run:")
        print("python test_product_skin_condition_similarity.py --product_id 123")
        print("python test_product_skin_condition_similarity.py --condition_id 456")
        return
    
    # Test product to skin conditions
    if args.product_id:
        test_product_to_conditions(args.product_id, args.top_n, args.similarity_threshold)
    
    # Test skin condition to products
    if args.condition_id:
        test_condition_to_products(args.condition_id, args.top_n, args.similarity_threshold)

if __name__ == "__main__":
    main()
