#!/usr/bin/env python
"""
Profile-Based Product Recommendation Module for SmartBeauty

This module:
1. Fetches user profile embedding from the database
2. Calculates similarity between user profile and all products
3. Returns top recommended products based on profile similarity
4. Supports allergen filtering and other constraints

Usage:
python profile_product_rec.py --user_id 2 [--top_n 10] [--max_price 100.0]
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from filtering_products.allergen.allergen_filtering import AllergenFilter
from db.connection import get_database_manager


class ProfileProductRecommendation:
    """
    Profile-based product recommendation system using user preference embeddings.
    
    This module:
    - Retrieves user profile embeddings
    - Calculates cosine similarity with product embeddings
    - Returns ranked product recommendations
    - Supports allergen filtering
    """
    
    def __init__(self):
        """Initialize the profile recommendation module."""
        self.allergen_filter = AllergenFilter()
    
    def recommend_products(
        self, 
        user_id: int,
        top_n: int = 10,
        max_price: Optional[float] = None,
        include_out_of_stock: bool = False
    ) -> Dict:
        """
        Complete profile-based recommendation pipeline.
        
        Args:
            user_id: User ID for recommendations
            top_n: Number of top products to return
            max_price: Optional maximum price filter
            include_out_of_stock: Whether to include out-of-stock products
            
        Returns:
            Dictionary with user profile info and product recommendations
        """
        print(f"Starting profile-based recommendations for user {user_id}")
        print(f"   Top products: {top_n}")
        print(f"   Max price: ${max_price}" if max_price else "   No price limit")
        print(f"   Include out of stock: {include_out_of_stock}")
        
        # Step 1: Get user profile embedding
        print(f"\nStep 1: Retrieving user profile embedding...")
        user_embedding = self._get_user_embedding(user_id)
        
        if not user_embedding:
            return {
                'user_id': user_id,
                'user_profile': {'message': 'User profile embedding not found'},
                'products': []
            }
        
        # Step 2: Get allergen filter components
        print(f"\nStep 2: Setting up allergen filtering...")
        allergen_where, allergen_params = self._get_allergen_filter(user_id)
        
        # Step 3: Calculate product similarities
        print(f"\nStep 3: Calculating product similarities...")
        products = self._calculate_product_similarities(
            user_embedding=user_embedding,
            allergen_where=allergen_where,
            allergen_params=allergen_params,
            top_n=top_n,
            max_price=max_price,
            include_out_of_stock=include_out_of_stock
        )
        
        # Step 4: Get user profile info
        user_profile_info = self._get_user_profile_info(user_id)
        
        return {
            'user_id': user_id,
            'user_profile': user_profile_info,
            'products': products,
            'parameters': {
                'top_n': top_n,
                'max_price': max_price,
                'include_out_of_stock': include_out_of_stock
            }
        }
    
    def _get_user_embedding(self, user_id: int) -> Optional[List[float]]:
        """Get user profile embedding from the database"""
        print(f"  Fetching user embedding for user {user_id}...")
        
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT embedding, embedding_text
                        FROM users
                        WHERE id = %s AND embedding IS NOT NULL
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    
                    if not result:
                        print(f"    No user found with ID {user_id} or user has no embedding")
                        return None
                    
                    embedding, embedding_text = result
                    
                    if embedding:
                        # Convert PostgreSQL vector to Python list
                        embedding_str = str(embedding)
                        if embedding_str.startswith('[') and embedding_str.endswith(']'):
                            embedding_list = [float(x.strip()) for x in embedding_str[1:-1].split(',')]
                            print(f"    Successfully retrieved user embedding ({len(embedding_list)}D)")
                            print(f"    User profile: {embedding_text[:100]}..." if embedding_text else "    No profile text")
                            return embedding_list
                        else:
                            print(f"    Invalid embedding format")
                            return None
                    else:
                        print(f"    User has no embedding")
                        return None
                        
        except Exception as e:
            print(f"    Database error: {e}")
            return None
    
    def _get_user_profile_info(self, user_id: int) -> Dict:
        """Get user profile information"""
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT embedding_text, created_at
                        FROM users
                        WHERE id = %s
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        embedding_text, created_at = result
                        return {
                            'user_id': user_id,
                            'profile_text': embedding_text,
                            'created_at': created_at.isoformat() if created_at else None,
                            'has_embedding': True
                        }
                    else:
                        return {
                            'user_id': user_id,
                            'message': 'User not found',
                            'has_embedding': False
                        }
                        
        except Exception as e:
            return {
                'user_id': user_id,
                'error': f"Database error: {e}",
                'has_embedding': False
            }
    
    def _get_allergen_filter(self, user_id: int) -> tuple:
        """Get allergen filter SQL components"""
        print(f"  Setting up allergen filtering...")
        
        try:
            # Get user allergens
            allergen_names, _ = self.allergen_filter.get_user_allergens(user_id)
            
            if not allergen_names:
                print(f"    No allergen restrictions")
                return "", []
            
            # Generate search terms
            search_terms = self.allergen_filter.generate_search_terms(allergen_names)
            
            # Get SQL components
            where_clause, params = self.allergen_filter.generate_allergen_filter_sql(
                search_terms, exclude_unsafe=True
            )
            
            print(f"    Allergen filter active: {len(allergen_names)} allergens")
            return where_clause, params
            
        except Exception as e:
            print(f"    Error setting up allergen filter: {e}")
            return "", []
    
    def _calculate_product_similarities(
        self,
        user_embedding: List[float],
        allergen_where: str,
        allergen_params: List[str],
        top_n: int,
        max_price: Optional[float],
        include_out_of_stock: bool
    ) -> List[Dict]:
        """Calculate product similarities using a single SQL query"""
        print(f"  Calculating product similarities using single query...")
        
        if not user_embedding:
            print("    No user embedding available, cannot calculate similarities.")
            return []
        
        try:
            # Build the WHERE clause
            where_conditions = ["embedding IS NOT NULL"]
            query_params = []
            
            if allergen_where:
                where_conditions.append(f"({allergen_where})")
                query_params.extend(allergen_params)
            
            if max_price:
                where_conditions.append("price <= %s")
                query_params.append(max_price)
            
            if not include_out_of_stock:
                where_conditions.append("stock_status = 0")
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Build the query with similarity calculation
            # Convert cosine distance to similarity: 1 - distance
            query = f"""
            SELECT
                id, name, key_benefits, description, price, stock_status,
                (1 - (embedding <=> %s::vector)) AS similarity_score
            FROM products
            {where_clause}
            ORDER BY similarity_score DESC
            LIMIT %s
            """
            
            # Add user embedding as first parameter
            query_params.insert(0, str(user_embedding))
            query_params.append(top_n)
            
            products = []
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, query_params)
                    results = cursor.fetchall()
                    
                    print(f"    Found {len(results)} products with similarity scores")
                    
                    for row in results:
                        (product_id, name, benefits, description, price, 
                         stock_status, similarity_score) = row
                        
                        products.append({
                            'id': product_id,
                            'name': name,
                            'key_benefits': benefits,
                            'description': description,
                            'price': float(price) if price else 0.0,
                            'stock_status': stock_status,
                            'in_stock': stock_status == 0,
                            'similarity_score': float(similarity_score) if similarity_score else 0.0
                        })
            
            print(f"  Successfully calculated similarities for {len(products)} products")
            return products
            
        except Exception as e:
            print(f"  Database error: {e}")
            return []


def display_results(results: Dict, verbose: bool = False):
    """Display recommendation results in a user-friendly format"""
    print(f"\n{'='*80}")
    print(f"Profile-Based Product Recommendations for User {results['user_id']}")
    print(f"{'='*80}")
    
    # User profile summary
    user_profile = results['user_profile']
    if 'message' in user_profile:
        print(f"User Profile: {user_profile['message']}")
        return
    elif 'error' in user_profile:
        print(f"Error: {user_profile['error']}")
        return
    
    print(f"User Profile Summary:")
    print(f"   User ID: {user_profile['user_id']}")
    print(f"   Has Embedding: {'Yes' if user_profile['has_embedding'] else 'No'}")
    print(f"   Created: {user_profile.get('created_at', 'Unknown')}")
    
    if verbose and user_profile.get('profile_text'):
        print(f"   Profile Text: {user_profile['profile_text'][:200]}...")
    
    # Product results
    products = results['products']
    if not products:
        print(f"\nNo products found matching the criteria.")
        return
    
    print(f"\nTop {len(products)} Recommended Products:")
    print(f"{'-'*80}")
    
    for i, product in enumerate(products, 1):
        print(f"{i}. {product['name']} (ID: {product['id']})")
        print(f"   Similarity: {product['similarity_score']:.4f} | Price: ${product['price']:.2f}")
        print(f"   Stock: {'In Stock' if product['in_stock'] else 'Out of Stock'}")
        
        if verbose:
            print(f"   Benefits: {product['key_benefits'][:100]}..." if product.get('key_benefits') else "   No benefits listed")
            if product.get('description'):
                print(f"   Description: {product['description'][:150]}...")
        
        print()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Profile-based product recommendations")
    parser.add_argument("--user_id", type=int, required=True, help="User ID for recommendations")
    parser.add_argument("--top_n", type=int, default=10, help="Number of top products to return")
    parser.add_argument("--max_price", type=float, help="Maximum product price")
    parser.add_argument("--include_out_of_stock", action="store_true", help="Include out-of-stock products")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed results")
    parser.add_argument("--output", help="Output file for results (JSON)")
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()
    
    print("SmartBeauty Profile-Based Product Recommendation")
    print("=" * 50)
    
    # Initialize recommendation module
    recommender = ProfileProductRecommendation()
    
    # Get recommendations
    results = recommender.recommend_products(
        user_id=args.user_id,
        top_n=args.top_n,
        max_price=args.max_price,
        include_out_of_stock=args.include_out_of_stock
    )
    
    # Display results
    display_results(results, verbose=args.verbose)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
