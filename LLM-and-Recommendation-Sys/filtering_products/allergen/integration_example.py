#!/usr/bin/env python
"""
Example of how AnalysisModule would integrate with AllergenFilter.

This demonstrates the complete integration pattern for using 
AllergenFilter components in a larger analysis system.
"""

import sys
import os
from typing import List, Dict, Optional

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from filtering_products.allergen_filtering import AllergenFilter
from db.connection import get_database_manager


class AnalysisModuleExample:
    """
    Example Analysis Module that integrates allergen filtering
    with other product analysis features.
    """
    
    def __init__(self):
        self.allergen_filter = AllergenFilter()
    
    def analyze_products_for_user(
        self, 
        user_id: int,
        max_price: float = 100.0,
        include_out_of_stock: bool = False,
        similarity_vector: Optional[List[float]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Complete product analysis with allergen filtering, price filtering,
        stock filtering, and optional similarity ranking.
        
        Args:
            user_id: User ID for allergen preferences
            max_price: Maximum product price
            include_out_of_stock: Whether to include out-of-stock products
            similarity_vector: Optional embedding vector for similarity search
            limit: Maximum number of results
            
        Returns:
            List of analyzed products with safety and ranking information
        """
        print(f"🔍 Analyzing products for user {user_id}")
        print(f"   Price limit: ${max_price}")
        print(f"   Include out of stock: {include_out_of_stock}")
        print(f"   Similarity search: {'Yes' if similarity_vector else 'No'}")
        print(f"   Result limit: {limit}")
        
        # Step 1: Get allergen filter components
        allergen_where, allergen_params = self._get_allergen_filter(user_id)
        
        # Step 2: Build comprehensive query
        query, params = self._build_analysis_query(
            allergen_where=allergen_where,
            allergen_params=allergen_params,
            max_price=max_price,
            include_out_of_stock=include_out_of_stock,
            similarity_vector=similarity_vector,
            limit=limit
        )
        
        # Step 3: Execute query
        products = self._execute_analysis_query(query, params)
        
        # Step 4: Post-process results
        analyzed_products = self._post_process_results(products, user_id)
        
        print(f"✅ Analysis complete: {len(analyzed_products)} products found")
        return analyzed_products
    
    def _get_allergen_filter(self, user_id: int) -> tuple:
        """Get allergen filter SQL components"""
        print(f"  📡 Getting allergen preferences...")
        
        # Get user allergens
        allergen_names, preferences = self.allergen_filter.get_user_allergens(user_id)
        
        if not allergen_names:
            print(f"  ✅ No allergen restrictions")
            return "", []
        
        # Generate search terms
        search_terms = self.allergen_filter.generate_search_terms(allergen_names)
        
        # Get SQL components
        where_clause, params = self.allergen_filter.generate_allergen_filter_sql(
            search_terms, exclude_unsafe=True
        )
        
        print(f"  🛡️  Allergen filter active: {len(allergen_names)} allergens, {len(params)} search terms")
        return where_clause, params
    
    def _build_analysis_query(
        self,
        allergen_where: str,
        allergen_params: List[str],
        max_price: float,
        include_out_of_stock: bool,
        similarity_vector: Optional[List[float]],
        limit: int
    ) -> tuple:
        """Build the comprehensive analysis SQL query"""
        print(f"  🏗️  Building analysis query...")
        
        # Base SELECT with conditional similarity
        if similarity_vector:
            select_clause = """
            SELECT 
                id, name, key_benefits, description, active_content,
                ingredients_text, price, stock_status, country,
                1 - (embedding <=> %s::vector) AS similarity_score
            """
            similarity_param = [str(similarity_vector)]
            order_by = "ORDER BY similarity_score DESC"
        else:
            select_clause = """
            SELECT 
                id, name, key_benefits, description, active_content,
                ingredients_text, price, stock_status, country,
                0.0 AS similarity_score
            """
            similarity_param = []
            order_by = "ORDER BY price ASC"
        
        # Build WHERE conditions
        where_conditions = []
        params = similarity_param.copy()
        
        # Add allergen filter if present
        if allergen_where:
            where_conditions.append(f"({allergen_where})")
            params.extend(allergen_params)
        
        # Add price filter
        where_conditions.append("price <= %s")
        params.append(str(max_price))
        
        # Add stock filter if needed
        if not include_out_of_stock:
            where_conditions.append("stock_status = 0")
        
        # Add embedding filter for similarity search
        if similarity_vector:
            where_conditions.append("embedding IS NOT NULL")
        
        # Combine query parts
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        {select_clause}
        FROM products 
        {where_clause}
        {order_by}
        LIMIT %s
        """
        
        params.append(str(limit))
        
        print(f"  📝 Query built: {len(where_conditions)} conditions, {len(params)} parameters")
        return query, params
    
    def _execute_analysis_query(self, query: str, params: List[str]) -> List[tuple]:
        """Execute the analysis query"""
        print(f"  ⚡ Executing analysis query...")
        
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    print(f"  ✅ Query successful: {len(results)} products retrieved")
                    return results
        
        except Exception as e:
            print(f"  ❌ Query failed: {e}")
            return []
    
    def _post_process_results(self, products: List[tuple], user_id: int) -> List[Dict]:
        """Post-process results with additional analysis"""
        print(f"  🔄 Post-processing {len(products)} products...")
        
        # Get allergen info for detailed analysis
        allergen_names, _ = self.allergen_filter.get_user_allergens(user_id)
        search_terms = {}
        if allergen_names:
            search_terms = self.allergen_filter.generate_search_terms(allergen_names)
        
        analyzed_products = []
        
        for product in products:
            (product_id, name, benefits, description, active_content, 
             ingredients, price, stock_status, country, similarity) = product
            
            # Analyze allergen safety in detail
            detected_allergens = []
            if search_terms and ingredients:
                detected_allergens = self.allergen_filter.detect_allergens_in_text(
                    ingredients, search_terms
                )
            
            # Create comprehensive product analysis
            analyzed_product = {
                'id': product_id,
                'name': name,
                'key_benefits': benefits,
                'description': description,
                'active_content': active_content,
                'ingredients_text': ingredients,
                'price': float(price) if price else 0.0,
                'stock_status': stock_status,
                'country': country,
                'similarity_score': float(similarity) if similarity else 0.0,
                'allergen_safety': {
                    'is_safe': len(detected_allergens) == 0,
                    'detected_allergens': detected_allergens,
                    'user_allergens': allergen_names
                },
                'availability': {
                    'in_stock': stock_status == 0,
                    'stock_status': stock_status
                }
            }
            
            analyzed_products.append(analyzed_product)
        
        return analyzed_products


def test_integration_example():
    """Test the integration example"""
    print("🧪 Testing AnalysisModule Integration Example")
    print("=" * 60)
    
    analysis_module = AnalysisModuleExample()
    
    # Test 1: Basic analysis with allergen filtering
    print("\n🔬 Test 1: Basic analysis with price and allergen filtering")
    print("-" * 50)
    
    results = analysis_module.analyze_products_for_user(
        user_id=3,
        max_price=75.0,
        include_out_of_stock=False,
        limit=5
    )
    
    if results:
        print(f"\n📊 Sample Results:")
        for i, product in enumerate(results[:3], 1):
            print(f"{i}. {product['name']} - ${product['price']}")
            print(f"   Allergen Safety: {'✅ Safe' if product['allergen_safety']['is_safe'] else '❌ Unsafe'}")
            print(f"   Stock: {'✅ In Stock' if product['availability']['in_stock'] else '❌ Out of Stock'}")
            if product['similarity_score'] > 0:
                print(f"   Similarity: {product['similarity_score']:.4f}")
            print()
    
    # Test 2: Analysis without allergen restrictions
    print("\n🔬 Test 2: Analysis for user without allergens")
    print("-" * 50)
    
    results = analysis_module.analyze_products_for_user(
        user_id=1,  # Assuming user 1 has no allergens
        max_price=50.0,
        limit=3
    )
    
    print(f"Found {len(results)} products for user without allergen restrictions")


if __name__ == "__main__":
    test_integration_example()
