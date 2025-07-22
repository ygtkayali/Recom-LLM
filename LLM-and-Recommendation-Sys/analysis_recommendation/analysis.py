#!/usr/bin/env python
"""
Analysis Module for SmartBeauty Product Recommendations

This module:
1. Fetches user skin analysis data from API
2. Filters analysis results by confidence threshold
3. Maps analysis types to skin concerns using embeddings
4. Calculates product scores based on concern similarities and confidence
5. Returns top recommended products with allergen filtering

Usage:
python analysis.py --user_id 2 [--threshold 0.5] [--top_n 10]
"""

import os
import sys
import argparse
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)
from utility.get_analysis import get_user_analysis
from filtering_products.allergen.allergen_filtering import AllergenFilter
from mapping import SPECIAL_MAPPINGS, BeautyPreferencesSkinConcern
from db.connection import get_database_manager


class ProductAnalysisModule:
    """
    Main analysis module for product recommendations based on skin analysis.
    
    This module integrates:
    - Skin analysis confidence filtering
    - Concern-to-embedding similarity matching
    - Allergen filtering
    - Weighted product scoring
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize the analysis module.
        
        Args:
            confidence_threshold: Minimum confidence score for analysis results (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self.allergen_filter = AllergenFilter()
        self.concern_embeddings_cache = {}  # Cache for concern embeddings
    
    def analyze_and_recommend(
        self, 
        user_id: int,
        top_n: int = 10,
        max_price: float = None,
        include_out_of_stock: bool = False,
        alpha: float = 0.8
    ) -> Dict:
        """
        Complete analysis and recommendation pipeline.
        
        Args:
            user_id: User ID for analysis and profile similarity
            top_n: Number of top products to return
            max_price: Optional maximum price filter
            include_out_of_stock: Whether to include out-of-stock products
            alpha: Weight for concern vs profile scoring (0.8 = 80% concern, 20% profile)
            
        Returns:
            Dictionary with analysis results and product recommendations
        """
        print(f"🔍 Starting analysis for user {user_id}")
        print(f"   Confidence threshold: {self.confidence_threshold}")
        print(f"   Top products: {top_n}")
        print(f"   Max price: ${max_price}" if max_price else "   No price limit")
        print(f"   Profile weight (1-α): {1-alpha:.1f}, Concern weight (α): {alpha:.1f}")
        
        # Step 1: Get and filter analysis data
        print(f"\n📊 Step 1: Fetching and filtering analysis data...")
        filtered_analysis = self._get_filtered_analysis(user_id)
        
        if not filtered_analysis:
            return {
                'user_id': user_id,
                'analysis_summary': {'message': 'No analysis data above threshold'},
                'products': []
            }
        
        # Step 2: Map analysis types to concerns
        print(f"\n🗺️  Step 2: Mapping analysis to skin concerns...")
        concern_scores = self._map_analysis_to_concerns(filtered_analysis)
        
        # Step 3: Get concern embeddings
        print(f"\n🧠 Step 3: Retrieving concern embeddings...")
        concern_embeddings = self._get_concern_embeddings(list(concern_scores.keys()))
        
        # Step 4: Get allergen filter components
        print(f"\n🛡️  Step 4: Setting up allergen filtering...")
        allergen_where, allergen_params = self._get_allergen_filter(user_id)
        
        # Step 5: Calculate product scores
        print(f"\n🎯 Step 5: Calculating product scores...")
        products = self._calculate_product_scores(
            concern_embeddings=concern_embeddings,
            concern_scores=concern_scores,
            allergen_where=allergen_where,
            allergen_params=allergen_params,
            user_id=user_id,
            alpha=alpha,
            top_n=top_n,
            max_price=max_price,
            include_out_of_stock=include_out_of_stock
        )
        
        # Step 6: Compile results
        analysis_summary = self._create_analysis_summary(filtered_analysis, concern_scores)
        
        return {
            'user_id': user_id,
            'analysis_summary': analysis_summary,
            'products': products,
            'parameters': {
                'confidence_threshold': self.confidence_threshold,
                'top_n': top_n,
                'max_price': max_price,
                'include_out_of_stock': include_out_of_stock
            }
        }
    
    def _get_filtered_analysis(self, user_id: int) -> List[Dict]:
        """Get analysis data and filter by confidence threshold"""
        print(f"  📡 Fetching analysis data...")
        
        analysis_data = get_user_analysis(user_id)
        if not analysis_data or not analysis_data.get('success'):
            print(f"  ❌ Failed to get analysis data")
            return []
        
        raw_analysis = analysis_data.get('data', [])
        print(f"  📋 Raw analysis items: {len(raw_analysis)}")
        
        # Filter by confidence threshold
        # Note: Some confidence values might be 0-100 scale, others 0-1 scale
        filtered = []
        for item in raw_analysis:
            confidence = item.get('confidence', 0)
            analysis_type = item.get('analysisType', '')
            
            # Normalize confidence to 0-1 scale
            if confidence > 1:
                normalized_confidence = confidence / 100.0
            else:
                normalized_confidence = confidence
            
            if normalized_confidence >= self.confidence_threshold:
                item['normalized_confidence'] = normalized_confidence
                filtered.append(item)
                print(f"    ✅ {analysis_type}: {confidence} → {normalized_confidence:.3f}")
            else:
                print(f"    ❌ {analysis_type}: {confidence} → {normalized_confidence:.3f} (below threshold)")
        
        print(f"  📊 Filtered analysis items: {len(filtered)}")
        return filtered
    
    def _map_analysis_to_concerns(self, analysis_data: List[Dict]) -> Dict[str, float]:
        """Map analysis types to skin concerns with weighted scores"""
        print(f"  🗺️  Mapping {len(analysis_data)} analysis items to concerns...")
        
        concern_scores = {}
        
        for item in analysis_data:
            analysis_type = item.get('analysisType', '').lower()
            confidence = item.get('normalized_confidence', 0)
            
            # Direct mapping - analysis type becomes concern name
            # The robust matching in _get_concern_embeddings will handle finding the right concept
            concern_scores[analysis_type] = concern_scores.get(analysis_type, 0) + confidence
            print(f"    📍 {analysis_type} → {analysis_type} (confidence: {confidence:.3f})")
        
        print(f"  📊 Final concern scores:")
        for concern, score in concern_scores.items():
            print(f"    {concern}: {score:.3f}")
        
        return concern_scores
    
    def _get_concern_embeddings(self, concern_names: List[str]) -> Dict[str, List[float]]:
        """Get embeddings for concerns from the concepts table with robust matching"""
        print(f"  🧠 Retrieving embeddings for {len(concern_names)} concerns...")
        
        concern_embeddings = {}
        
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get all available concepts first for better matching
                    cursor.execute("""
                    SELECT name, embedding 
                    FROM concepts 
                    WHERE embedding IS NOT NULL
                    ORDER BY name
                    """)
                    
                    available_concepts = cursor.fetchall()
                    print(f"    📋 Available concepts: {[name for name, _ in available_concepts]}")
                    
                    for concern in concern_names:
                        matched_concept = None
                        
                        # Try multiple matching strategies
                        normalized_concern = concern.lower().replace(' ', '').replace('-', '').replace('_', '')
                        
                        for concept_name, embedding in available_concepts:
                            normalized_concept = concept_name.lower().replace(' ', '').replace('-', '').replace('_', '')
                            
                            # Strategy 1: Exact match after normalization
                            if normalized_concern == normalized_concept:
                                matched_concept = (concept_name, embedding)
                                break
                            
                            # Strategy 2: Concern contains concept or vice versa
                            elif (normalized_concern in normalized_concept or 
                                  normalized_concept in normalized_concern):
                                matched_concept = (concept_name, embedding)
                                break
                            
                            # Strategy 3: Special known mappings based on actual database content
                            elif self._is_concept_match(normalized_concern, normalized_concept):
                                matched_concept = (concept_name, embedding)
                                break
                        
                        if matched_concept:
                            concept_name, embedding = matched_concept
                            
                            # Convert PostgreSQL vector to Python list
                            if embedding:
                                embedding_str = str(embedding)
                                if embedding_str.startswith('[') and embedding_str.endswith(']'):
                                    embedding_list = [float(x.strip()) for x in embedding_str[1:-1].split(',')]
                                    concern_embeddings[concern] = embedding_list
                                    print(f"    ✅ {concern} → {concept_name} (embedding: {len(embedding_list)}D)")
                                else:
                                    print(f"    ⚠️  {concern} → {concept_name} (invalid embedding format)")
                            else:
                                print(f"    ⚠️  {concern} → {concept_name} (no embedding)")
                        else:
                            print(f"    ❌ {concern} → No matching concept found")
        
        except Exception as e:
            print(f"  ❌ Database error: {e}")
        
        print(f"  📊 Retrieved {len(concern_embeddings)} concern embeddings")
        return concern_embeddings
    
    def _is_concept_match(self, concern: str, concept: str) -> bool:
        """Check if concern matches concept using known mappings"""
        # Known mappings based on actual database concepts
        mappings = {
            'darkcircles': 'darkcircles',
            'puffiness': 'eyebag',  # puffiness maps to Eyebag concept
            'finelines': 'wrinkles',
            'finelineswrinkles': 'wrinkles',
            'acneblemishes': 'acne',  # This exists as 'Acne' in database
            'blemishes': 'acne'
        }
        
        return mappings.get(concern) == concept
    
    def _get_allergen_filter(self, user_id: int) -> Tuple[str, List[str]]:
        """Get allergen filter SQL components"""
        print(f"  🛡️  Setting up allergen filtering...")
        
        # Get user allergens
        allergen_names, _ = self.allergen_filter.get_user_allergens(user_id)
        
        if not allergen_names:
            print(f"    ✅ No allergen restrictions")
            return "", []
        
        # Generate search terms
        search_terms = self.allergen_filter.generate_search_terms(allergen_names)
        
        # Get SQL components
        where_clause, params = self.allergen_filter.generate_allergen_filter_sql(
            search_terms, exclude_unsafe=True
        )
        
        print(f"    🛡️  Allergen filter active: {len(allergen_names)} allergens")
        return where_clause, params
    
    def _calculate_product_scores(
        self,
        concern_embeddings: Dict[str, List[float]],
        concern_scores: Dict[str, float],
        allergen_where: str,
        allergen_params: List[str],
        user_id: int,
        alpha: float,
        top_n: int,
        max_price: Optional[float],
        include_out_of_stock: bool
    ) -> List[Dict]:
        """Calculate weighted product scores combining concern analysis and user profile similarity."""
        print(f"  🎯 Calculating weighted product scores (α={alpha:.1f} concern, {1-alpha:.1f} profile)...")
    
        if not concern_embeddings:
            print("    ⚠️  No concern embeddings available, using profile similarity only.")
            return self._calculate_profile_only_scores(user_id, allergen_where, allergen_params, top_n, max_price, include_out_of_stock)

        # --- Step 1: Build the components for the weighted scoring query ---

        # Build the concern-based scoring formula first
        concern_score_clauses = []
        concern_params = []

        for concern_name, embedding in concern_embeddings.items():
            weight = concern_scores.get(concern_name, 0)
            # Convert distance to similarity: 1 - distance
            concern_score_clauses.append(f"({weight} * (1 - (p.embedding <=> %s::vector)))")
            concern_params.append(str(embedding))

        # Build concern formula once
        concern_scoring_formula = " + ".join(concern_score_clauses) if concern_score_clauses else "0"
        
        # For the final score, we need separate parameters for the repeated concern formula
        final_score_concern_params = concern_params.copy()  # Duplicate for final score calculation

        # Build the WHERE clause conditions
        where_conditions = [
            "p.embedding IS NOT NULL",
            "u.embedding IS NOT NULL", 
            "u.id = %s"
        ]
        
        # Initialize query parameters: concern embeddings (for concern_score), concern embeddings (for final_score), user ID
        query_params = concern_params + final_score_concern_params + [user_id]
        
        if allergen_where:
            where_conditions.append(f"({allergen_where})")
            query_params.extend(allergen_params)

        if max_price:
            where_conditions.append("p.price <= %s")
            query_params.append(max_price)

        if not include_out_of_stock:
            where_conditions.append("p.stock_status = 0")

        where_clause = "WHERE " + " AND ".join(where_conditions)

        # --- Step 2: Assemble the weighted scoring query ---
        # Build the final score formula using the duplicated parameters
        final_score_clauses = []
        for concern_name, embedding in concern_embeddings.items():
            weight = concern_scores.get(concern_name, 0)
            final_score_clauses.append(f"({weight} * (1 - (p.embedding <=> %s::vector)))")
        
        final_score_concern_formula = " + ".join(final_score_clauses) if final_score_clauses else "0"
        
        final_query = f"""
        SELECT
            p.id, p.name, p.key_benefits, p.description, p.price, p.stock_status,
            ({concern_scoring_formula}) AS concern_score,
            (1 - (u.embedding <=> p.embedding)) AS profile_score,
            ({alpha} * ({final_score_concern_formula})) + ({1-alpha} * (1 - (u.embedding <=> p.embedding))) AS final_score
        FROM products p
        CROSS JOIN users u
        {where_clause}
        ORDER BY final_score DESC
        LIMIT %s
        """
        query_params.append(top_n)

        # --- Step 3: Execute the weighted scoring query ---

        products = []
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(final_query, query_params)
                    results = cursor.fetchall()

                    print(f"      📈 Found {len(results)} products with weighted scores.")
                    
                    for row in results:
                        (product_id, name, benefits, description, price, 
                        stock_status, concern_score, profile_score, final_score) = row
                        
                        products.append({
                            'id': product_id,
                            'name': name,
                            'key_benefits': benefits,
                            'description': description,
                            'price': float(price) if price else 0.0,
                            'stock_status': stock_status,
                            'in_stock': stock_status == 0,
                            'concern_score': float(concern_score) if concern_score else 0.0,
                            'profile_score': float(profile_score) if profile_score else 0.0,
                            'final_score': float(final_score) if final_score else 0.0,
                            'total_score': float(final_score) if final_score else 0.0,  # Keep for backward compatibility
                            'concern_scores': {}  # Individual concern breakdown not available in single query
                        })
                        
        except Exception as e:
            print(f"  ❌ Database error in weighted scoring: {e}")
            
            # Fallback to concern-only scoring if user profile is not available
            print("  🔄 Falling back to concern-only scoring...")
            return self._calculate_concern_only_scores(concern_embeddings, concern_scores, allergen_where, allergen_params, top_n, max_price, include_out_of_stock)

        print(f"  ✅ Weighted scoring complete, returning top {len(products)} products.")
        return products
    
    def _calculate_profile_only_scores(
        self, 
        user_id: int, 
        allergen_where: str, 
        allergen_params: List[str], 
        top_n: int, 
        max_price: Optional[float], 
        include_out_of_stock: bool
    ) -> List[Dict]:
        """Fallback to profile-only scoring when no concern embeddings are available."""
        print(f"  🔄 Using profile-only scoring...")
        
        where_conditions = [
            "p.embedding IS NOT NULL",
            "u.embedding IS NOT NULL",
            "u.id = %s"
        ]
        
        query_params = [user_id]
        
        if allergen_where:
            where_conditions.append(f"({allergen_where})")
            query_params.extend(allergen_params)
        
        if max_price:
            where_conditions.append("p.price <= %s")
            query_params.append(max_price)
        
        if not include_out_of_stock:
            where_conditions.append("p.stock_status = 0")
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            p.id, p.name, p.key_benefits, p.description, p.price, p.stock_status,
            (1 - (u.embedding <=> p.embedding)) AS profile_score
        FROM products p
        CROSS JOIN users u
        {where_clause}
        ORDER BY profile_score DESC
        LIMIT %s
        """
        query_params.append(top_n)
        
        products = []
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, query_params)
                    results = cursor.fetchall()
                    
                    for row in results:
                        (product_id, name, benefits, description, price, stock_status, profile_score) = row
                        
                        products.append({
                            'id': product_id,
                            'name': name,
                            'key_benefits': benefits,
                            'description': description,
                            'price': float(price) if price else 0.0,
                            'stock_status': stock_status,
                            'in_stock': stock_status == 0,
                            'concern_score': 0.0,
                            'profile_score': float(profile_score) if profile_score else 0.0,
                            'final_score': float(profile_score) if profile_score else 0.0,
                            'total_score': float(profile_score) if profile_score else 0.0,
                            'concern_scores': {}
                        })
        except Exception as e:
            print(f"  ❌ Profile-only scoring failed: {e}")
            return []
        
        return products
    
    def _calculate_concern_only_scores(
        self,
        concern_embeddings: Dict[str, List[float]],
        concern_scores: Dict[str, float],
        allergen_where: str,
        allergen_params: List[str],
        top_n: int,
        max_price: Optional[float],
        include_out_of_stock: bool
    ) -> List[Dict]:
        """Fallback to concern-only scoring when user profile is not available."""
        print(f"  🔄 Using concern-only scoring...")
        
        score_clauses = []
        query_params = []

        for concern_name, embedding in concern_embeddings.items():
            weight = concern_scores.get(concern_name, 0)
            score_clauses.append(f"({weight} * (1 - (embedding <=> %s::vector)))")
            query_params.append(str(embedding))

        scoring_formula = " + ".join(score_clauses)

        where_conditions = ["embedding IS NOT NULL"]
        
        if allergen_where:
            where_conditions.append(f"({allergen_where})")
            query_params.extend(allergen_params)

        if max_price:
            where_conditions.append("price <= %s")
            query_params.append(max_price)

        if not include_out_of_stock:
            where_conditions.append("stock_status = 0")

        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = f"""
        SELECT
            id, name, key_benefits, description, price, stock_status,
            ({scoring_formula}) AS concern_score
        FROM products
        {where_clause}
        ORDER BY concern_score DESC
        LIMIT %s
        """
        query_params.append(top_n)

        products = []
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, query_params)
                    results = cursor.fetchall()
                    
                    for row in results:
                        (product_id, name, benefits, description, price, stock_status, concern_score) = row
                        
                        products.append({
                            'id': product_id,
                            'name': name,
                            'key_benefits': benefits,
                            'description': description,
                            'price': float(price) if price else 0.0,
                            'stock_status': stock_status,
                            'in_stock': stock_status == 0,
                            'concern_score': float(concern_score) if concern_score else 0.0,
                            'profile_score': 0.0,
                            'final_score': float(concern_score) if concern_score else 0.0,
                            'total_score': float(concern_score) if concern_score else 0.0,
                            'concern_scores': {}
                        })
        except Exception as e:
            print(f"  ❌ Concern-only scoring failed: {e}")
            return []
        
        return products
    
    def _create_analysis_summary(self, filtered_analysis: List[Dict], concern_scores: Dict[str, float]) -> Dict:
        """Create summary of analysis results"""
        return {
            'total_analysis_items': len(filtered_analysis),
            'confidence_threshold': self.confidence_threshold,
            'analysis_items': [
                {
                    'type': item.get('analysisType'),
                    'confidence': item.get('confidence'),
                    'normalized_confidence': item.get('normalized_confidence'),
                    'created_at': item.get('createdAt')
                }
                for item in filtered_analysis
            ],
            'mapped_concerns': concern_scores,
            'top_concerns': sorted(concern_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        }


def display_results(results: Dict, verbose: bool = False):
    """Display analysis results in a user-friendly format"""
    print(f"\n{'='*80}")
    print(f"📊 PRODUCT ANALYSIS RESULTS FOR USER {results['user_id']}")
    print(f"{'='*80}")
    
    # Analysis summary
    summary = results['analysis_summary']
    if 'message' in summary:
        print(f"📋 {summary['message']}")
        return
    
    print(f"📋 Analysis Summary:")
    print(f"   Confidence threshold: {summary['confidence_threshold']}")
    print(f"   Analysis items processed: {summary['total_analysis_items']}")
    print(f"   Top concerns: {', '.join([f'{c}({s:.2f})' for c, s in summary['top_concerns']])}")
    
    # Product results
    products = results['products']
    print(f"\n🎯 Top {len(products)} Recommended Products:")
    print(f"{'-'*80}")
    
    for i, product in enumerate(products, 1):
        print(f"{i}. {product['name']} (ID: {product['id']})")
        print(f"   Final Score: {product['final_score']:.4f} | Price: ${product['price']:.2f}")
        print(f"   Concern Score: {product.get('concern_score', 0):.4f} | Profile Score: {product.get('profile_score', 0):.4f}")
        print(f"   Stock: {'✅ In Stock' if product['in_stock'] else '❌ Out of Stock'}")
        
        if verbose:
            print(f"   Benefits: {product['key_benefits'][:100]}..." if product.get('key_benefits') else "")
            print(f"   Concern breakdown:")
            for concern, scores in product['concern_scores'].items():
                print(f"     - {concern}: similarity={scores['similarity']:.3f}, weight={scores['weight']:.3f}, score={scores['weighted_score']:.4f}")
        
        print()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Analyze skin concerns and recommend products")
    parser.add_argument("--user_id", type=int, required=True, help="User ID for analysis")
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold (0.0-1.0)")
    parser.add_argument("--top_n", type=int, default=10, help="Number of top products to return")
    parser.add_argument("--max_price", type=float, help="Maximum product price")
    parser.add_argument("--alpha", type=float, default=0.8, help="Weight for concern vs profile (0.8 = 80% concern, 20% profile)")
    parser.add_argument("--include_out_of_stock", action="store_true", help="Include out-of-stock products")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed results")
    parser.add_argument("--output", help="Output file for results (JSON)")
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()
    
    print(f"🧪 SmartBeauty Product Analysis Module")
    print(f"{'='*50}")
    
    # Initialize analysis module
    analysis_module = ProductAnalysisModule(confidence_threshold=args.threshold)
    
    # Run analysis and recommendations
    results = analysis_module.analyze_and_recommend(
        user_id=args.user_id,
        top_n=args.top_n,
        max_price=args.max_price,
        alpha=args.alpha,
        include_out_of_stock=args.include_out_of_stock
    )
    
    # Display results
    display_results(results, verbose=args.verbose)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {args.output}")


if __name__ == "__main__":
    main()
