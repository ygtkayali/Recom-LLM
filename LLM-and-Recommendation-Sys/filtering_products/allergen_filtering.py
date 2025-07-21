#!/usr/bin/env python
"""
Allergen Filtering System for SmartBeauty Products

This module provides comprehensive allergen filtering functionality:
1. Fetches user preferences from API
2. Maps allergen IDs to names using the mapping system
3. Uses the allergen detector to generate search terms
4. Filters products from database based on ingredient content

Usage:
python allergen_filtering.py --user_id 2 [--dry_run] [--verbose]
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Set, Tuple, Optional

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from utility.get_preference import get_user_analysis
from mapping import AllergenicIngredients
from filtering_products.allergen_detector import default_detector
from db.connection import get_database_manager


class AllergenFilter:
    """
    Allergen filtering component that generates SQL filter conditions.
    
    This class does not execute database queries. Instead, it generates
    SQL WHERE clause components and parameters that can be used by 
    other modules (like AnalysisModule) to build comprehensive queries.
    """
    
    def __init__(self):
        self.detector = default_detector
        self.allergen_mapping = AllergenicIngredients
        
    def get_user_allergens(self, user_id: int) -> Tuple[List[str], Dict]:
        """
        Fetch user preferences and extract allergen names.
        
        Args:
            user_id: User ID to fetch preferences for
            
        Returns:
            Tuple of (allergen_names_list, full_preferences_dict)
        """
        print(f"📡 Fetching preferences for user {user_id}...")
        
        # Get user preferences from API
        preferences = get_user_analysis(user_id)
        if not preferences:
            print(f"❌ Failed to fetch preferences for user {user_id}")
            return [], {}
        
        # Extract allergenic ingredients
        allergen_ids = preferences.get('allergenicIngredients', [])
        print(f"🧪 Found {len(allergen_ids)} allergen ID(s): {allergen_ids}")
        
        # Map IDs to names
        allergen_names = []
        for allergen_id in allergen_ids:
            if allergen_id in self.allergen_mapping:
                allergen_name = self.allergen_mapping[allergen_id]
                allergen_names.append(allergen_name)
                print(f"   ID {allergen_id} → {allergen_name}")
            else:
                print(f"⚠️  Unknown allergen ID: {allergen_id}")
        
        return allergen_names, preferences
    
    def generate_search_terms(self, allergen_names: List[str]) -> Dict[str, List[str]]:
        """
        Generate database search terms for each allergen.
        
        Args:
            allergen_names: List of allergen names
            
        Returns:
            Dictionary mapping allergen_name -> search_terms_list
        """
        print(f"🔍 Generating search terms for {len(allergen_names)} allergen(s)...")
        
        search_terms_map = {}
        for allergen in allergen_names:
            terms = self.detector.generate_search_terms(allergen)
            search_terms_map[allergen] = terms
            print(f"   {allergen}: {terms}")
        
        return search_terms_map
    
    def generate_allergen_filter_sql(
        self, 
        allergen_search_terms: Dict[str, List[str]],
        exclude_unsafe: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Generate SQL WHERE clause components for allergen filtering.
        
        Args:
            allergen_search_terms: Dictionary mapping allergen -> search terms
            exclude_unsafe: If True, generates filter to exclude products with allergens.
                           If False, generates filter to include only products with allergens.
            
        Returns:
            Tuple of (where_clause_snippet, parameters_list)
            
        Example:
            where_clause = "NOT (ingredients_text ILIKE %s OR ingredients_text ILIKE %s)"
            parameters = ["%nickel%", "%parabens%"]
        """
        if not allergen_search_terms:
            print("⚠️  No allergen search terms provided, returning empty filter")
            return "", []
        
        # Collect all search terms from all allergens
        all_search_terms = []
        for allergen, terms in allergen_search_terms.items():
            all_search_terms.extend(terms)
        
        if not all_search_terms:
            print("⚠️  No search terms generated, returning empty filter")
            return "", []
        
        print(f"🔍 Generating SQL filter for {len(all_search_terms)} allergen search terms...")
        
        # Create ILIKE conditions for each search term
        ilike_conditions = []
        parameters = []
        
        for term in all_search_terms:
            ilike_conditions.append("ingredients_text ILIKE %s")
            parameters.append(f"%{term}%")
        
        # Combine all conditions with OR (any allergen match)
        combined_condition = f"({' OR '.join(ilike_conditions)})"
        
        # Apply NOT if we want to exclude unsafe products
        if exclude_unsafe:
            where_clause = f"NOT {combined_condition}"
            filter_type = "exclude unsafe"
        else:
            where_clause = combined_condition
            filter_type = "include unsafe only"
        
        print(f"✅ Generated allergen filter ({filter_type}): {len(parameters)} parameters")
        
        return where_clause, parameters
    
    def get_allergen_summary(self, allergen_search_terms: Dict[str, List[str]]) -> Dict:
        """
        Get a summary of allergen filtering configuration.
        
        Args:
            allergen_search_terms: Dictionary mapping allergen -> search terms
            
        Returns:
            Dictionary with allergen filtering summary information
        """
        total_terms = sum(len(terms) for terms in allergen_search_terms.values())
        
        return {
            'allergen_count': len(allergen_search_terms),
            'allergens': list(allergen_search_terms.keys()),
            'total_search_terms': total_terms,
            'search_terms_by_allergen': allergen_search_terms
        }
    
    def detect_allergens_in_text(
        self, 
        ingredients_text: str, 
        allergen_search_terms: Dict[str, List[str]]
    ) -> List[str]:
        """
        Detect which specific allergens are present in ingredients text.
        
        This is a utility function that can be used by other modules
        to analyze product ingredients after they've been retrieved.
        
        Args:
            ingredients_text: The ingredients text to analyze
            allergen_search_terms: Dictionary mapping allergen -> search terms
            
        Returns:
            List of allergen names detected in the text
        """
        detected = []
        if not ingredients_text:
            return detected
            
        ingredients_lower = ingredients_text.lower()
        
        for allergen, terms in allergen_search_terms.items():
            for term in terms:
                if term.lower() in ingredients_lower:
                    detected.append(allergen)
                    break  # Found this allergen, move to next
        
        return detected
    
class AllergenFilterTester:
    """
    Testing utilities for the AllergenFilter.
    
    This class demonstrates how to use the AllergenFilter components
    and provides testing functionality for the SQL generation.
    """
    
    def __init__(self):
        self.allergen_filter = AllergenFilter()
    
    def test_sql_generation(
        self, 
        user_id: int, 
        dry_run: bool = True,
        exclude_unsafe: bool = True
    ):
        """
        Test the SQL generation functionality.
        
        Args:
            user_id: User ID to test with
            dry_run: If True, only show SQL that would be generated
            exclude_unsafe: Whether to exclude or include unsafe products
        """
        print(f"🧪 Testing AllergenFilter SQL generation for user {user_id}")
        print(f"{'='*70}")
        
        # Step 1: Get user allergens
        allergen_names, preferences = self.allergen_filter.get_user_allergens(user_id)
        
        if not allergen_names:
            print("✅ User has no allergen restrictions - no SQL filter needed!")
            return None, []
        
        # Step 2: Generate search terms
        search_terms = self.allergen_filter.generate_search_terms(allergen_names)
        
        # Step 3: Generate SQL components
        where_clause, parameters = self.allergen_filter.generate_allergen_filter_sql(
            search_terms, exclude_unsafe=exclude_unsafe
        )
        
        # Step 4: Show results
        print(f"\n📊 Generated SQL Components:")
        print(f"{'-'*50}")
        print(f"WHERE clause snippet: {where_clause}")
        print(f"Parameters ({len(parameters)}): {parameters}")
        
        # Step 5: Show example usage
        self._show_example_usage(where_clause, parameters, dry_run)
        
        # Step 6: Show summary
        summary = self.allergen_filter.get_allergen_summary(search_terms)
        print(f"\n📈 Allergen Filter Summary:")
        print(f"{'-'*50}")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        return where_clause, parameters
    
    def _show_example_usage(self, where_clause: str, parameters: List[str], dry_run: bool):
        """Show example of how AnalysisModule would use these components"""
        if not where_clause:
            return
            
        print(f"\n� Example Usage in AnalysisModule:")
        print(f"{'-'*50}")
        
        # Example 1: Basic product filtering
        example_query = f"""
        SELECT 
            id, name, key_benefits, description, price, stock_status
        FROM products 
        WHERE {where_clause}
          AND stock_status = 0
          AND price <= %s
        ORDER BY price ASC
        LIMIT %s
        """
        
        example_params = parameters + ["100.00", "20"]
        
        print("Example Query (with price and stock filters):")
        print(example_query)
        print(f"Parameters: {example_params}")
        
        # Example 2: With similarity search
        print(f"\nExample with Vector Similarity:")
        similarity_query = f"""
        SELECT 
            id, name, key_benefits, description, price,
            1 - (embedding <=> %s::vector) AS similarity
        FROM products 
        WHERE {where_clause}
          AND stock_status = 0
          AND embedding IS NOT NULL
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        similarity_params = ["[0.1, 0.2, 0.3, ...]"] + parameters + ["10"]
        print(similarity_query)
        print(f"Parameters: {similarity_params}")
        
        if not dry_run:
            # Actually test the basic query
            print(f"\n🔍 Testing basic query execution...")
            self._test_query_execution(example_query, parameters + ["100.00", "10"])
    
    def _test_query_execution(self, query: str, parameters: List[str]):
        """Test actual query execution to verify SQL is valid"""
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, parameters)
                    results = cursor.fetchall()
                    
                    print(f"✅ Query executed successfully")
                    print(f"   Found {len(results)} products")
                    
                    if results:
                        print(f"   Sample result: {results[0][1]} (ID: {results[0][0]})")
        
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
    
    def test_allergen_detection(self, test_ingredients: str, user_id: int):
        """Test allergen detection in ingredient text"""
        print(f"🔬 Testing allergen detection in ingredient text")
        print(f"{'='*70}")
        
        # Get user allergens
        allergen_names, _ = self.allergen_filter.get_user_allergens(user_id)
        
        if not allergen_names:
            print("✅ User has no allergen restrictions")
            return
        
        # Generate search terms
        search_terms = self.allergen_filter.generate_search_terms(allergen_names)
        
        # Test detection
        detected = self.allergen_filter.detect_allergens_in_text(test_ingredients, search_terms)
        
        print(f"Test ingredients: {test_ingredients}")
        print(f"User allergens: {allergen_names}")
        print(f"Detected allergens: {detected}")
        print(f"Result: {'❌ UNSAFE' if detected else '✅ SAFE'}")
        
        return detected


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate SQL components for allergen-based product filtering")
    parser.add_argument("--user_id", type=int, required=True, help="User ID to fetch preferences for")
    parser.add_argument("--dry_run", action="store_true", default=True, help="Show SQL components without executing queries")
    parser.add_argument("--execute_test", action="store_true", help="Execute test queries to verify SQL validity")
    parser.add_argument("--exclude_unsafe", action="store_true", default=True, help="Generate filter to exclude unsafe products (default)")
    parser.add_argument("--include_unsafe_only", action="store_true", help="Generate filter to include only unsafe products")
    parser.add_argument("--test_ingredients", type=str, help="Test ingredient text for allergen detection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    return parser.parse_args()


def main():
    """Main function - demonstrates AllergenFilter usage"""
    args = parse_args()
    
    print(f"🧪 SmartBeauty Allergen Filter SQL Generator")
    print(f"{'='*60}")
    
    # Initialize tester
    tester = AllergenFilterTester()
    
    # Determine filter mode
    exclude_unsafe = not args.include_unsafe_only
    
    if args.test_ingredients:
        # Test allergen detection in provided ingredients
        print(f"\n🔬 Testing ingredient analysis:")
        tester.test_allergen_detection(args.test_ingredients, args.user_id)
    
    # Generate and test SQL components
    print(f"\n🧪 Generating SQL components:")
    where_clause, parameters = tester.test_sql_generation(
        user_id=args.user_id,
        dry_run=not args.execute_test,
        exclude_unsafe=exclude_unsafe
    )
    
    # Show usage instructions
    print(f"\n💡 Integration Instructions for AnalysisModule:")
    print(f"{'='*60}")
    print(f"1. Import: from filtering_products.allergen_filtering import AllergenFilter")
    print(f"2. Initialize: allergen_filter = AllergenFilter()")
    print(f"3. Get user allergens: allergen_names, _ = allergen_filter.get_user_allergens(user_id)")
    print(f"4. Generate search terms: search_terms = allergen_filter.generate_search_terms(allergen_names)")
    print(f"5. Get SQL components: where_clause, params = allergen_filter.generate_allergen_filter_sql(search_terms)")
    print(f"6. Build your query: 'SELECT ... FROM products WHERE ' + where_clause + ' AND your_conditions'")
    print(f"7. Execute with combined parameters: cursor.execute(query, params + your_params)")
    
    if where_clause:
        print(f"\n📋 Generated Components for User {args.user_id}:")
        print(f"   WHERE clause: {where_clause}")
        print(f"   Parameters: {parameters}")
    
    print(f"\n✅ AllergenFilter ready for integration!")


if __name__ == "__main__":
    main()
