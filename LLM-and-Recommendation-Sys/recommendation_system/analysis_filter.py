import json
try:
    from .mapping import BeautyPreferencesSkinType, BeautyPreferencesSkinConcern, SPECIAL_MAPPINGS, PREFERENCE_PRIORITY, AllergenicIngredients
    from .preference_rec.allergen_detector import default_detector
except ImportError:
    from mapping import BeautyPreferencesSkinType, BeautyPreferencesSkinConcern, SPECIAL_MAPPINGS, PREFERENCE_PRIORITY, AllergenicIngredients
    from preference_rec.allergen_detector import default_detector

def get_name_mappings():
    """Get reverse mappings from names to IDs"""
    concern_name_to_id = {v.lower(): k for k, v in BeautyPreferencesSkinConcern.items()}
    skin_type_name_to_id = {v.lower(): k for k, v in BeautyPreferencesSkinType.items()}
    return concern_name_to_id, skin_type_name_to_id

def validate_special_mappings():
    """Validate that all special mappings reference valid concern/skin type names"""
    concern_names = {v.lower() for v in BeautyPreferencesSkinConcern.values()}
    skin_type_names = {v.lower() for v in BeautyPreferencesSkinType.values()}
    
    # Validate concerns
    invalid_concerns = []
    for analysis_type, mapping in SPECIAL_MAPPINGS.items():
        if 'concerns' in mapping:
            for concern in mapping['concerns']:
                if concern.lower() not in concern_names:
                    invalid_concerns.append(f"{analysis_type} -> {concern}")
    
    # Validate skin types  
    invalid_skin_types = []
    for analysis_type, mapping in SPECIAL_MAPPINGS.items():
        if 'skinTypes' in mapping:
            for skin_type in mapping['skinTypes']:
                if skin_type.lower() not in skin_type_names:
                    invalid_skin_types.append(f"{analysis_type} -> {skin_type}")
    
    if invalid_concerns:
        print("WARNING: Invalid concern mappings found:")
        for invalid in invalid_concerns:
            print(f"  {invalid}")
        print(f"Available concerns: {sorted(concern_names)}")
    
    if invalid_skin_types:
        print("WARNING: Invalid skin type mappings found:")
        for invalid in invalid_skin_types:
            print(f"  {invalid}")
        print(f"Available skin types: {sorted(skin_type_names)}")
    
    return len(invalid_concerns) == 0 and len(invalid_skin_types) == 0

def find_matching_ids(analysis_type):
    """
    Find which mapping dictionary contains the analysis type and return the corresponding ID
    Returns tuple: (concern_ids, skin_type_ids)
    """
    concern_name_to_id, skin_type_name_to_id = get_name_mappings()
    concern_ids = []
    skin_type_ids = []
    
    # First check special mappings (case-insensitive)
    analysis_lower = analysis_type.lower()
    if analysis_lower in SPECIAL_MAPPINGS:
        mapping = SPECIAL_MAPPINGS[analysis_lower]
        if 'concerns' in mapping:
            for concern_name in mapping['concerns']:
                if concern_name in concern_name_to_id:
                    concern_ids.append(concern_name_to_id[concern_name])
                else:
                    print(f"  WARNING: Concern '{concern_name}' not found in mapping")
        if 'skinTypes' in mapping:
            for skin_type_name in mapping['skinTypes']:
                if skin_type_name in skin_type_name_to_id:
                    skin_type_ids.append(skin_type_name_to_id[skin_type_name])
                else:
                    print(f"  WARNING: Skin type '{skin_type_name}' not found in mapping")
    else:
        # Check if analysis type matches any concern directly (case-insensitive)
        if analysis_lower in concern_name_to_id:
            concern_ids.append(concern_name_to_id[analysis_lower])
        
        # Check if analysis type matches any skin type directly (case-insensitive)
        if analysis_lower in skin_type_name_to_id:
            skin_type_ids.append(skin_type_name_to_id[analysis_lower])
    
    return concern_ids, skin_type_ids
    
def filter_products_by_skin_analysis_api(skin_analysis_data, products_data, confidence_threshold=0.5, max_products_per_condition=5, user_preferences=None, return_format='detailed'):
    """
    Filter products based on skin analysis results and return product IDs grouped by condition
    
    Args:
        skin_analysis_data: Dict containing skin analysis results from API
        products_data: Dict containing products data
        confidence_threshold: Minimum confidence level to consider (default 0.5)
        max_products_per_condition: Maximum products to return per condition (default 5)
        user_preferences: Optional dict containing user preferences for personalized scoring
        return_format: 'detailed' for full product info with scores, 'ids_only' for backward compatibility
    
    Returns:
        If return_format='detailed':
        Dict with conditions as keys and product info as values, plus top_score element:
        {
            "top_score": [{"id": product_id, "score": score, "name": name}],
            "acne": [{"id": product_id, "score": score, "name": name}],
            ...
        }
        
        If return_format='ids_only':
        Dict with conditions as keys and product IDs as values: {"acne": [product_ids], ...}
    """
    # Find analysis types with confidence above threshold
    qualifying_conditions = []
    for analysis in skin_analysis_data['data']:
        if analysis['confidence'] >= confidence_threshold:
            qualifying_conditions.append(analysis['analysisType'])
    
    # Track all recommended products to avoid duplicates across conditions
    all_recommended_products = set()
    all_scored_products = []  # Track all products with scores for top_score
    results = {}
    
    # For each qualifying condition, find matching products
    for condition in qualifying_conditions:
        condition_products = []
        
        # Get the IDs for this analysis type
        concern_ids, skin_type_ids = find_matching_ids(condition)
        
        if concern_ids or skin_type_ids:
            # Find products that match these concerns or skin types
            for product in products_data['products']:
                # Get product ID
                product_id = product.get('id')
                if not product_id:
                    continue
                    
                # Skip if we already recommended this product
                if product_id in all_recommended_products:
                    continue
                
                product_concerns = product.get('concerns', [])
                product_skin_types = product.get('skinTypes', [])
                
                # Check if any concern ID matches
                concern_match = any(concern_id in product_concerns for concern_id in concern_ids)
                # Check if any skin type ID matches
                skin_type_match = any(skin_type_id in product_skin_types for skin_type_id in skin_type_ids)
                
                if concern_match or skin_type_match:
                    # Check for allergen safety first - exclude products with allergens
                    if user_preferences and not _is_product_safe_for_user(product, user_preferences):
                        continue  # Skip this product completely
                    
                    # Calculate preference score if user preferences provided
                    score = _calculate_preference_score(product, user_preferences) if user_preferences else 0.0
                    
                    product_info = {
                        "id": product_id,
                        "score": score,
                        "name": product.get('name', ''),
                        "concern_match": concern_match,
                        "skin_type_match": skin_type_match
                    }
                    
                    condition_products.append(product_info)
                    all_scored_products.append(product_info)
                    all_recommended_products.add(product_id)
        
        # Sort by score if user preferences provided, otherwise maintain original order
        if user_preferences and condition_products:
            condition_products.sort(key=lambda x: x["score"], reverse=True)
        
        # Limit products per condition
        condition_products = condition_products[:max_products_per_condition]
        
        # Always add condition to results, even if empty
        results[condition] = condition_products
    
    # Add top_score element with highest scoring products
    if user_preferences and all_scored_products:
        # Sort all products by score and take top 1-2
        all_scored_products.sort(key=lambda x: x["score"], reverse=True)
        results["top_score"] = all_scored_products[:2]  # Top 2 products
    
    # Return appropriate format based on return_format parameter
    if return_format == 'ids_only':
        # Convert to old format for backward compatibility
        ids_only_results = {}
        for condition, products in results.items():
            if condition != 'top_score':  # Exclude top_score from old format
                ids_only_results[condition] = [p["id"] if isinstance(p, dict) else p for p in products]
        return ids_only_results
    
    return results

def get_concern_name_from_id(concern_id):
    """Helper function to get concern name from ID"""
    return BeautyPreferencesSkinConcern.get(concern_id, f"Unknown concern (ID: {concern_id})")

def get_skin_type_name_from_id(skin_type_id):
    """Helper function to get skin type name from ID"""
    return BeautyPreferencesSkinType.get(skin_type_id, f"Unknown skin type (ID: {skin_type_id})")

# For backward compatibility and testing - loads data from JSON files
def filter_products_by_analysis_local(user_preferences_path=None):
    """
    Legacy function for testing - loads data from files and calls the main function
    
    Args:
        user_preferences_path: Optional path to user preferences JSON file
    """
    # Validate mappings first
    print("Validating special mappings...")
    if not validate_special_mappings():
        print("ERROR: Invalid mappings detected. Please fix before proceeding.")
        return {}
    print("✓ All mappings validated successfully")
    
    # Load skin analysis data
    with open('../skin_analysis.json', 'r') as f:
        skin_data = json.load(f)
    
    # Load products data
    with open('../product_cache.json', 'r') as f:
        products_data = json.load(f)
    
    # Load user preferences - try multiple paths
    user_preferences = None
    preference_paths = []
    
    if user_preferences_path:
        preference_paths.append(user_preferences_path)
    
    # Add default paths to search
    preference_paths.extend([
        '../user_preference.json',
        'user_preference.json',
        'test_user_preferences.json'
    ])
    
    for path in preference_paths:
        try:
            with open(path, 'r') as f:
                user_preferences = json.load(f)
            print(f"✓ Loaded user preferences from {path}")
            print(f"  - Skin Type: {user_preferences.get('skinType', 'Not specified')}")
            print(f"  - Skin Concerns: {user_preferences.get('skinConcerns', 'Not specified')}")
            print(f"  - Allergens to avoid: {len(user_preferences.get('allergenicIngredients', []))} ingredients")
            print(f"  - Age Range: {user_preferences.get('ageRange', 'Not specified')}")
            break
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"WARNING: Error loading preferences from {path}: {e}")
            continue
    
    if not user_preferences:
        print("WARNING: No user preferences file found. Using skin analysis only.")
    
    return filter_products_by_skin_analysis_api(skin_data, products_data, user_preferences=user_preferences)

def _calculate_preference_score(product, user_preferences):
    """
    Calculate preference score based on user preferences and priority levels
    
    Args:
        product: Product dictionary
        user_preferences: User preferences dictionary with IDs as used in the mapping
    
    Returns:
        float: Total preference score (0.0 to 1.0)
    """
    if not user_preferences:
        return 0.0
    
    # Priority level weights
    priority_weights = {
        "CRITICAL": 0.4,  # 40% of total score
        "HIGH": 0.3,      # 30% of total score  
        "MEDIUM": 0.2,    # 20% of total score
        "LOW": 0.1        # 10% of total score
    }
    
    total_score = 0.0
    
    # CRITICAL: Must match - binary scoring
    critical_score = _score_critical_preferences(product, user_preferences)
    total_score += critical_score * priority_weights["CRITICAL"]
    
    # HIGH: Very important - weighted scoring
    high_score = _score_high_preferences(product, user_preferences)
    total_score += high_score * priority_weights["HIGH"]
    
    # MEDIUM: Important - basic scoring
    medium_score = _score_medium_preferences(product, user_preferences)
    total_score += medium_score * priority_weights["MEDIUM"]
    
    # LOW: Nice to have - minimal scoring
    low_score = _score_low_preferences(product, user_preferences)
    total_score += low_score * priority_weights["LOW"]
    
    return min(total_score, 1.0)  # Cap at 1.0

def _score_critical_preferences(product, user_preferences):
    """Score CRITICAL preferences: skinType, skinConcerns (allergens filtered out earlier)"""
    score = 0.0
    scored_items = 0
    
    # Check skin type compatibility
    user_skin_type = user_preferences.get('skinType', 0)
    if user_skin_type != 0:
        scored_items += 1
        product_skin_types = product.get('skinTypes', [])
        if user_skin_type in product_skin_types or 1 in product_skin_types:  # 1 = "All"
            score += 1.0
    
    # Check skin concerns compatibility
    user_concerns = user_preferences.get('skinConcerns', [])
    if user_concerns and user_concerns != [0]:
        scored_items += 1
        product_concerns = set(product.get('concerns', []))
        user_concerns_set = set(c for c in user_concerns if c != 0)
        if user_concerns_set.intersection(product_concerns):
            overlap_score = len(user_concerns_set.intersection(product_concerns)) / len(user_concerns_set)
            score += overlap_score
    
    # Note: Allergen safety is handled by filtering out unsafe products earlier
    # No need to check allergens here since unsafe products are already excluded
    
    return score / scored_items if scored_items > 0 else 0.0

def _score_high_preferences(product, user_preferences):
    """Score HIGH preferences: skinTone, ageRange"""
    score = 0.0
    scored_items = 0
    
    # Age range compatibility (text-based heuristic)
    user_age_range = user_preferences.get('ageRange', 0)
    if user_age_range != 0:
        scored_items += 1
        product_text = f"{product.get('name', '')} {product.get('description', '')} {product.get('keyBenefits', '')}".lower()
        
        # Age-appropriate keywords scoring
        age_keywords = {
            1: ["teen", "young", "gentle", "acne"],      # SixteenPlus
            2: ["daily", "hydrating", "preventive"],     # Twenties
            3: ["anti-aging", "preventive", "firming"],  # Thirties
            4: ["anti-aging", "firming", "mature"],      # Forties
            5: ["anti-aging", "intensive", "renewal"]    # FiftyPlus
        }
        
        keywords = age_keywords.get(user_age_range, [])
        if keywords:
            matches = sum(1 for keyword in keywords if keyword in product_text)
            score += min(matches / len(keywords), 1.0)
    
    # Skin tone compatibility (basic heuristic)
    user_skin_tone = user_preferences.get('skinTone', 0)
    if user_skin_tone != 0:
        scored_items += 1
        # Basic implementation - could be enhanced with more sophisticated matching
        score += 0.5  # Neutral score for now
    
    return score / scored_items if scored_items > 0 else 0.0

def _score_medium_preferences(product, user_preferences):
    """Score MEDIUM preferences: fragrancePreferences, hairType, shoppingPreferences"""
    score = 0.0
    scored_items = 0
    
    # Basic scoring for medium preferences
    medium_prefs = ['fragrancePreferences', 'hairType', 'shoppingPreferences']
    for pref in medium_prefs:
        user_pref = user_preferences.get(pref, [])
        if user_pref and user_pref != [0]:
            scored_items += 1
            score += 0.3  # Basic score for having medium preferences
    
    return score / scored_items if scored_items > 0 else 0.0

def _score_low_preferences(product, user_preferences):
    """Score LOW preferences: eyeColor, hairColor, favoriteBrands"""
    score = 0.0
    scored_items = 0
    
    # Basic scoring for low preferences
    low_prefs = ['eyeColor', 'hairColor', 'favoriteBrands']
    for pref in low_prefs:
        user_pref = user_preferences.get(pref)
        if user_pref and user_pref != 0:
            scored_items += 1
            score += 0.2  # Basic score for having low preferences
    
    return score / scored_items if scored_items > 0 else 0.0

def _is_product_safe_for_user(product, user_preferences):
    """Check if product is safe for user (contains no excluded allergens)"""
    user_allergens = user_preferences.get('allergenicIngredients', [])
    if not user_allergens or user_allergens == [0]:
        return True  # No allergen restrictions
    
    allergen_names = [AllergenicIngredients.get(a) for a in user_allergens if a != 0]
    if not allergen_names:
        return True  # No valid allergen names
    
    product_content = f"{product.get('contents', '')} {product.get('activeContent', '')}"
    return default_detector.is_safe_for_user(product_content, allergen_names)


if __name__ == "__main__":
    print("=== Smart Beauty Product Recommendation System ===")
    print("Analyzing skin conditions with confidence > 0.5...")
    
    results = filter_products_by_analysis_local()
    
    print("\n=== RESULTS ===")
    
    if not results:
        print("No products found matching the analysis criteria.")
    else:
        # Show top score products first if available
        if 'top_score' in results:
            print("🏆 TOP RECOMMENDATIONS:")
            for i, product in enumerate(results['top_score'], 1):
                if isinstance(product, dict):
                    print(f"  {i}. {product['name']} (Score: {product['score']:.3f})")
                else:
                    print(f"  {i}. Product ID: {product}")
            print()
        
        # Show condition-specific recommendations
        total_products = 0
        conditions_count = 0
        
        for condition, products in results.items():
            if condition != 'top_score':
                conditions_count += 1
                total_products += len(products)
                print(f"📋 {condition.upper()} ({len(products)} products):")
                for i, product in enumerate(products, 1):
                    if isinstance(product, dict):
                        score_text = f" (Score: {product['score']:.3f})" if 'score' in product else ""
                        print(f"  {i}. {product['name']}{score_text}")
                    else:
                        print(f"  {i}. Product ID: {product}")
                print()
        
        print("=== SUMMARY ===")
        print(f"Total unique products recommended: {total_products}")
        print(f"Conditions addressed: {conditions_count}")
        
        if 'top_score' in results:
            print("✨ Personalized recommendations based on user preferences included!")
        else:
            print("💡 Add user preferences for personalized scoring!")
