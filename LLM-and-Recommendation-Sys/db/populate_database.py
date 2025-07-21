#!/usr/bin/env python
"""
Comprehensive script to populate both products and concepts tables from JSON files.

This script:
1. Populates products table from product_cache.json
2. Populates concepts table from concept_descriptions.json  
3. Provides options to truncate tables before insertion
4. Shows detailed progress and statistics

Table Schemas:
PRODUCTS:
- id (serial), name, key_benefits, description, active_content
- ingredients_text, how_to_use, price, stock_status, is_on_sale, country
- embedding (vector), created_at, updated_at

CONCEPTS:  
- id (int), concept_type, name, description
- embedding (vector), created_at, updated_at

Usage:
python populate_database.py [--truncate-products] [--truncate-concepts] [--batch-size 500]
"""
import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# Import local modules using new connection system
from db.connection import get_database_manager, test_db_connection
from db.utils import check_table_exists, truncate_table, get_table_row_count


def load_products_from_json(filepath: str) -> List[Dict[str, Any]]:
    """
    Load products from product_cache.json.
    
    Args:
        filepath: Path to the product JSON file
        
    Returns:
        List of product dictionaries
    """
    try:
        print(f"📂 Loading products from {filepath}...")
        
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract products from the cache structure
        products = []
        if isinstance(data, dict) and "products" in data:
            products = data["products"]
            print(f"✅ Successfully loaded {len(products)} products from cache")
        else:
            print(f"❌ Unexpected data structure in {filepath}")
            return []
            
        return products
        
    except Exception as e:
        print(f"❌ Error loading products: {e}")
        return []


def load_concepts_from_json(filepath: str) -> List[Dict[str, Any]]:
    """
    Load concepts from concept_descriptions.json.
    
    Args:
        filepath: Path to the concept JSON file
        
    Returns:
        List of concept dictionaries
    """
    try:
        print(f"📂 Loading concepts from {filepath}...")
        
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            concepts_data = json.load(f)
        
        if isinstance(concepts_data, list):
            print(f"✅ Successfully loaded {len(concepts_data)} concepts")
            return concepts_data
        else:
            print(f"❌ Expected list but got {type(concepts_data)}")
            return []
            
    except Exception as e:
        print(f"❌ Error loading concepts: {e}")
        return []


def extract_product_data(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and clean product data for the products table schema.
    
    Args:
        product: Raw product dictionary from cache
        
    Returns:
        Cleaned product data dictionary
    """
    def safe_get(data, key, default=""):
        """Safely get a value from dictionary with fallbacks."""
        value = data.get(key, default)
        if isinstance(value, (list, dict)):
            return json.dumps(value) if value else default
        return str(value) if value is not None else default
    
    def safe_price(data, price_key, default=0.0):
        """Safely extract price as numeric value."""
        price_value = data.get(price_key, default)
        try:
            return float(price_value) if price_value is not None else default
        except (ValueError, TypeError):
            return default
    
    # Map product cache fields to database schema
    extracted_data = {
        'name': safe_get(product, 'name', 'Unknown Product'),
        'key_benefits': safe_get(product, 'keyBenefits') or safe_get(product, 'key_benefits'),
        'description': safe_get(product, 'description'),
        'active_content': safe_get(product, 'activeContent') or safe_get(product, 'active_content'),
        'ingredients_text': safe_get(product, 'contents') or safe_get(product, 'ingredients'),
        'how_to_use': safe_get(product, 'howToUse') or safe_get(product, 'how_to_use'),
        'price': safe_price(product, 'price'),
        'stock_status': product.get('stockStatus', 0),  # 0 = in stock
        'is_on_sale': safe_price(product, 'discountedPrice') > 0,
        'country': safe_get(product, 'country', 'Turkey')  # Default based on Purgene brand
    }
    
    # Create embeddings_text by concatenating specified fields
    embeddings_parts = []
    
    # 1. keyBenefits, activeContent, name
    key_benefits = safe_get(product, 'keyBenefits') or safe_get(product, 'key_benefits')
    active_content = safe_get(product, 'activeContent') or safe_get(product, 'active_content')
    name = safe_get(product, 'name', 'Unknown Product')
    
    if key_benefits:
        embeddings_parts.append(f"Key Benefits: {key_benefits}")
    if active_content:
        embeddings_parts.append(f"Active Content: {active_content}")
    if name:
        embeddings_parts.append(f"Product Name: {name}")
    
    # 2. description
    description = safe_get(product, 'description')
    if description:
        embeddings_parts.append(f"Description: {description}")
    
    # 3. contents, howToUse, timeOfUse
    contents = safe_get(product, 'contents') or safe_get(product, 'ingredients')
    how_to_use = safe_get(product, 'howToUse') or safe_get(product, 'how_to_use')
    time_of_use = safe_get(product, 'timeOfUse') or safe_get(product, 'time_of_use')
    
    if contents:
        embeddings_parts.append(f"Ingredients: {contents}")
    if how_to_use:
        embeddings_parts.append(f"How to Use: {how_to_use}")
    if time_of_use:
        embeddings_parts.append(f"Time of Use: {time_of_use}")
    
    # Join all parts with double newline for clear separation
    extracted_data['embeddings_text'] = "\n\n".join(embeddings_parts)
    
    return extracted_data


def extract_concept_data(concept: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and clean concept data for the concepts table schema.
    
    Args:
        concept: Raw concept dictionary
        
    Returns:
        Cleaned concept data dictionary
    """
    return {
        'id': concept.get('id'),
        'concept_type': concept.get('type', 'skin_concern'),  # Use type from JSON, default to skin_concern
        'name': concept.get('name', ''),
        'description': concept.get('description', '')
    }


def insert_products_batch(products: List[Dict[str, Any]], batch_size: int = 500) -> int:
    """
    Insert products into the database in batches.
    
    Args:
        products: List of product dictionaries
        batch_size: Number of products to insert per batch
        
    Returns:
        Number of products successfully inserted
    """
    if not products:
        print("⚠️ No products to insert")
        return 0
    
    total_inserted = 0
    total_batches = (len(products) + batch_size - 1) // batch_size
    
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                for batch_idx in range(0, len(products), batch_size):
                    batch = products[batch_idx:batch_idx + batch_size]
                    current_batch_num = (batch_idx // batch_size) + 1
                    
                    print(f"📦 Processing products batch {current_batch_num}/{total_batches} ({len(batch)} products)...")
                    
                    insert_query = """
                        INSERT INTO products (
                            name, key_benefits, description, active_content, 
                            ingredients_text, how_to_use, embeddings_text, price, stock_status, 
                            is_on_sale, country
                        ) VALUES (
                            %(name)s, %(key_benefits)s, %(description)s, %(active_content)s,
                            %(ingredients_text)s, %(how_to_use)s, %(embeddings_text)s, %(price)s, %(stock_status)s,
                            %(is_on_sale)s, %(country)s
                        )
                    """
                    
                    batch_data = []
                    for product in batch:
                        try:
                            extracted_data = extract_product_data(product)
                            batch_data.append(extracted_data)
                        except Exception as e:
                            print(f"⚠️ Error processing product {product.get('name', 'Unknown')}: {e}")
                            continue
                    
                    if batch_data:
                        cursor.executemany(insert_query, batch_data)
                        conn.commit()
                        inserted_count = len(batch_data)
                        total_inserted += inserted_count
                        print(f"✅ Products batch {current_batch_num} completed: {inserted_count} products inserted")
                    else:
                        print(f"⚠️ Products batch {current_batch_num} skipped: no valid products")
                
                print(f"🎉 Total products inserted: {total_inserted}")
                return total_inserted
                
    except Exception as e:
        print(f"❌ Error during products batch insert: {e}")
        return total_inserted


def insert_concepts_batch(concepts: List[Dict[str, Any]]) -> int:
    """
    Insert concepts into the database.
    
    Args:
        concepts: List of concept dictionaries
        
    Returns:
        Number of concepts successfully inserted
    """
    if not concepts:
        print("⚠️ No concepts to insert")
        return 0
    
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                print(f"📦 Processing {len(concepts)} concepts...")
                
                insert_query = """
                    INSERT INTO concepts (
                        id, concept_type, name, description
                    ) VALUES (
                        %(id)s, %(concept_type)s, %(name)s, %(description)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        concept_type = EXCLUDED.concept_type,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                batch_data = []
                for concept in concepts:
                    try:
                        extracted_data = extract_concept_data(concept)
                        if extracted_data['id'] is not None:  # Ensure we have an ID
                            batch_data.append(extracted_data)
                        else:
                            print(f"⚠️ Skipping concept without ID: {concept.get('name', 'Unknown')}")
                    except Exception as e:
                        print(f"⚠️ Error processing concept {concept.get('name', 'Unknown')}: {e}")
                        continue
                
                if batch_data:
                    cursor.executemany(insert_query, batch_data)
                    conn.commit()
                    print(f"✅ Successfully inserted/updated {len(batch_data)} concepts")
                    return len(batch_data)
                else:
                    print("❌ No valid concepts to insert")
                    return 0
                
    except Exception as e:
        print(f"❌ Error during concepts insert: {e}")
        return 0


def get_file_paths() -> Tuple[str, str]:
    """
    Get the paths to the JSON files.
    
    Returns:
        Tuple of (product_file_path, concept_file_path)
    """
    # Try different possible locations for product_cache.json
    product_paths = [
        os.path.join(os.path.dirname(__file__), "product_cache.json"),
        os.path.join(parent_dir, "product_cache.json"),
        "product_cache.json"
    ]
    
    product_file = None
    for path in product_paths:
        if os.path.exists(path):
            product_file = path
            break
    
    # Use the first path as default if not found
    if not product_file:
        product_file = product_paths[0]
    
    # Concept file should be in db folder
    concept_file = os.path.join(os.path.dirname(__file__), "concept_descriptions.json")
    
    return product_file, concept_file


def show_table_statistics():
    """Show current table statistics."""
    print("\n📊 Current Table Statistics:")
    print("-" * 40)
    
    for table_name in ['products', 'concepts']:
        if check_table_exists(table_name):
            row_count = get_table_row_count(table_name)
            
            # Check embeddings if table has them
            embedding_info = ""
            try:
                with get_database_manager().get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
                        with_embeddings = cursor.fetchone()[0]
                        if with_embeddings > 0:
                            embedding_info = f" ({with_embeddings} with embeddings)"
            except:
                pass
            
            print(f"  ✅ {table_name}: {row_count} rows{embedding_info}")
        else:
            print(f"  ❌ {table_name}: table does not exist")


def main():
    """Main function to populate both tables."""
    parser = argparse.ArgumentParser(description='Populate SmartBeauty database from JSON files')
    parser.add_argument('--truncate-products', action='store_true', 
                       help='Truncate products table before inserting')
    parser.add_argument('--truncate-concepts', action='store_true', 
                       help='Truncate concepts table before inserting')
    parser.add_argument('--truncate-all', action='store_true',
                       help='Truncate both tables before inserting')
    parser.add_argument('--batch-size', type=int, default=500,
                       help='Batch size for products insertion (default: 500)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be inserted without actually inserting')
    parser.add_argument('--products-only', action='store_true',
                       help='Only populate products table')
    parser.add_argument('--concepts-only', action='store_true',
                       help='Only populate concepts table')
    parser.add_argument('--show-stats', action='store_true',
                       help='Show current table statistics and exit')
    
    args = parser.parse_args()
    
    print("🚀 SmartBeauty Database Population Script")
    print("=" * 60)
    
    # Show statistics if requested
    if args.show_stats:
        if not test_db_connection():
            print("❌ Database connection failed")
            return False
        show_table_statistics()
        return True
    
    # Test database connection
    if not test_db_connection():
        print("❌ Database connection failed. Please check your configuration.")
        return False
    
    # Check if required tables exist
    tables_to_check = []
    if not args.concepts_only:
        tables_to_check.append('products')
    if not args.products_only:
        tables_to_check.append('concepts')
    
    for table_name in tables_to_check:
        if not check_table_exists(table_name):
            print(f"❌ {table_name} table does not exist. Please run table_creation.py first.")
            return False
    
    print("✅ Required tables exist")
    
    # Show current statistics
    show_table_statistics()
    
    # Get file paths
    product_file, concept_file = get_file_paths()
    
    success_results = {}
    
    # Handle products
    if not args.concepts_only:
        print(f"\n🛍️ PRODUCTS TABLE POPULATION")
        print("=" * 40)
        print(f"📁 Using product file: {product_file}")
        
        # Truncate if requested
        if args.truncate_products or args.truncate_all:
            if truncate_table('products'):
                print("✅ Products table truncated")
            else:
                print("❌ Failed to truncate products table")
                return False
        
        # Load and process products
        products = load_products_from_json(product_file)
        if not products:
            print("❌ No products loaded")
            success_results['products'] = False
        else:
            print(f"📊 Loaded {len(products)} products")
            
            if args.dry_run:
                print("\n🔍 Dry run mode - showing sample product data:")
                print("-" * 30)
                sample_product = extract_product_data(products[0])
                for key, value in sample_product.items():
                    display_value = str(value)[:80] + '...' if len(str(value)) > 80 else str(value)
                    print(f"  {key}: {display_value}")
            else:
                # Insert products
                start_time = datetime.now()
                inserted_count = insert_products_batch(products, args.batch_size)
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"\n🎯 Products Summary:")
                print(f"  Products processed: {len(products)}")
                print(f"  Products inserted: {inserted_count}")
                print(f"  Success rate: {(inserted_count/len(products)*100):.1f}%")
                print(f"  Processing time: {duration.total_seconds():.2f} seconds")
                
                success_results['products'] = inserted_count > 0
    
    # Handle concepts
    if not args.products_only:
        print(f"\n🧠 CONCEPTS TABLE POPULATION")
        print("=" * 40)
        print(f"📁 Using concept file: {concept_file}")
        
        # Truncate if requested
        if args.truncate_concepts or args.truncate_all:
            if truncate_table('concepts'):
                print("✅ Concepts table truncated")
            else:
                print("❌ Failed to truncate concepts table")
                return False
        
        # Load and process concepts
        concepts = load_concepts_from_json(concept_file)
        if not concepts:
            print("❌ No concepts loaded")
            success_results['concepts'] = False
        else:
            print(f"📊 Loaded {len(concepts)} concepts")
            
            # Show type distribution
            type_counts = {}
            for concept in concepts:
                concept_type = concept.get('type', 'unknown')
                type_counts[concept_type] = type_counts.get(concept_type, 0) + 1
            
            print("📋 Concept type distribution:")
            for concept_type, count in type_counts.items():
                print(f"  - {concept_type}: {count} concepts")
            
            if args.dry_run:
                print("\n🔍 Dry run mode - showing sample concept data:")
                print("-" * 30)
                sample_concept = extract_concept_data(concepts[0])
                for key, value in sample_concept.items():
                    display_value = str(value)[:80] + '...' if len(str(value)) > 80 else str(value)
                    print(f"  {key}: {display_value}")
            else:
                # Insert concepts
                start_time = datetime.now()
                inserted_count = insert_concepts_batch(concepts)
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"\n🎯 Concepts Summary:")
                print(f"  Concepts processed: {len(concepts)}")
                print(f"  Concepts inserted: {inserted_count}")
                print(f"  Success rate: {(inserted_count/len(concepts)*100):.1f}%")
                print(f"  Processing time: {duration.total_seconds():.2f} seconds")
                
                success_results['concepts'] = inserted_count > 0
    
    # Show final statistics if not dry run
    if not args.dry_run:
        show_table_statistics()
    
    # Overall success
    overall_success = all(success_results.values()) if success_results else True
    
    if args.dry_run:
        print("\n🔍 Dry run completed - no data was actually inserted")
    else:
        print(f"\n{'🎉' if overall_success else '⚠️'} Database population completed!")
        
        print("\n💡 Next steps:")
        print("  - Run: python db/check_database_tables.py --detailed")
        print("  - Generate embeddings with your embedding creation script")
        print("  - Test vector search functionality")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
