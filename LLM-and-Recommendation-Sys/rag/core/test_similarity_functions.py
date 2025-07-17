#!/usr/bin/env python
"""
Test script to demonstrate finding related skin conditions for products
and related products for skin conditions using embedding similarities.
"""
import sys
import os

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Now we can import from the core module
from utils import get_related_skin_conditions_for_product, get_related_products_for_skin_condition

def test_product_to_skin_conditions():
    """Test finding related skin conditions for a product."""
    print("=" * 60)
    print("Testing: Find Related Skin Conditions for Product")
    print("=" * 60)
    
    # Test with product ID "2" (we saw this in the sample data)
    product_id = "39"
    print(f"\nFinding skin conditions related to product ID: {product_id}")
    
    related_conditions = get_related_skin_conditions_for_product(product_id, top_n=3)
    
    if related_conditions:
        print(f"\nTop 3 related skin conditions:")
        for i, condition in enumerate(related_conditions, 1):
            print(f"\n{i}. {condition['condition_name']} (ID: {condition['condition_id']})")
            print(f"   Similarity: {condition['similarity']:.4f}")
            print(f"   Description: {condition['document'][:100]}...")
    else:
        print("No related skin conditions found.")

def test_skin_condition_to_products():
    """Test finding related products for a skin condition."""
    print("\n" + "=" * 60)
    print("Testing: Find Related Products for Skin Condition")
    print("=" * 60)
    
    # Test with skin condition ID "1" (we saw this in the sample data)
    condition_id = "1"
    print(f"\nFinding products related to skin condition ID: {condition_id}")
    
    related_products = get_related_products_for_skin_condition(condition_id, top_n=3)
    
    if related_products:
        print(f"\nTop 3 related products:")
        for i, product in enumerate(related_products, 1):
            print(f"\n{i}. {product['product_name']} (ID: {product['product_id']})")
            print(f"   Similarity: {product['similarity']:.4f}")
            print(f"   Description: {product['document'][:100]}...")
    else:
        print("No related products found.")

def list_available_items():
    """List available products and skin conditions for testing."""
    print("\n" + "=" * 60)
    print("Available Items for Testing")
    print("=" * 60)
    
    from utils import create_db_connection_from_config
    import json
    
    conn = create_db_connection_from_config()
    if conn:
        cursor = conn.cursor()
        
        # List products
        print("\nAvailable Products:")
        cursor.execute("""
        SELECT cmetadata
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'products'
        )        ORDER BY (cmetadata->>'product_id')::int
        """)
        products = cursor.fetchall()
        
        for product in products:
            metadata = product[0]  # Already a dict, no need to parse JSON
            print(f"  - ID: {metadata.get('product_id')}, Name: {metadata.get('name')}")
        
        # List skin conditions
        print("\nAvailable Skin Conditions:")
        cursor.execute("""
        SELECT cmetadata
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'skin_conditions'
        )
        ORDER BY (cmetadata->>'condition_id')::int
        """)
        conditions = cursor.fetchall()
        
        for condition in conditions:
            metadata = condition[0]  # Already a dict, no need to parse JSON
            print(f"  - ID: {metadata.get('condition_id')}, Name: {metadata.get('condition_name')}")
        
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔍 Testing Product-Skin Condition Similarity Functions")
    
    # List available items first
    list_available_items()
    
    # Test product to skin conditions
    test_product_to_skin_conditions()
    
    # Test skin condition to products  
    test_skin_condition_to_products()
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete!")
    print("=" * 60)
