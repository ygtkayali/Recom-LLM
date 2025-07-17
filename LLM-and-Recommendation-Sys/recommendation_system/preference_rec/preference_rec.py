import json
from typing import Dict, List, Tuple, Optional
from .user_preference_parser import UserPreferenceParser
from .allergen_detector import default_detector

class PreferenceRecommendationEngine:
    def __init__(self, products_data: Dict = None, user_preferences_data: Dict = None):
        """
        Initialize with API data instead of file paths
        
        Args:
            products_data: Products data from API (dict with 'products' key)
            user_preferences_data: User preferences data from API 
        """
        if products_data:
            self.products_data = products_data
        else:
            self.products_data = {"products": []}
            
        self.parser = UserPreferenceParser()
        
        if user_preferences_data:
            self.parsed_prefs = self.parser.parse_preferences_from_data(user_preferences_data)
        else:
            self.parsed_prefs = {
                "product_skin_types": set(),
                "product_concerns": set(),
                "excluded_ingredients": [],
                "critical_filters": {},
                "high_priority_filters": {},
                "medium_priority_filters": {},
                "low_priority_filters": {}
            }
    
    def get_recommendations(self, max_products: int = 20) -> Dict[str, any]:
        """Get product recommendations based on user preferences"""
        
        # Stage 1: Apply critical filters (must match)
        candidates = self._apply_critical_filters(self.products_data["products"])
        
        if not candidates:
            return {"success": False, "message": "No products match critical criteria"}
        
        # Stage 2: Apply high priority filters and score
        scored_products = self._apply_high_priority_scoring(candidates)
        
        # Stage 3: Apply medium and low priority scoring
        final_scores = self._apply_additional_scoring(scored_products)
        
        # Stage 4: Sort and limit results
        recommendations = sorted(final_scores, key=lambda x: x["total_score"], reverse=True)
        
        return {
            "success": True,
            "total_candidates": len(candidates),
            "recommendations": recommendations[:max_products],
            "filters_applied": self._get_applied_filters_summary()
        }
    
    def _apply_critical_filters(self, products: List[Dict]) -> List[Dict]:
        """Apply filters that products MUST satisfy"""
        filtered = []
        
        for product in products:
            # Check skin type compatibility
            if not self._check_skin_type_compatibility(product):
                continue
            
            # Check allergen exclusions
            if not self._check_allergen_safety(product):
                continue
                
            # Check age appropriateness (if specified)
            if not self._check_age_appropriateness(product):
                continue
            
            filtered.append(product)
        
        return filtered
    
    def _check_skin_type_compatibility(self, product: Dict) -> bool:
        """Check if product is compatible with user's skin type"""
        user_skin_types = self.parsed_prefs["product_skin_types"]
        product_skin_types = set(product.get("skinTypes", []))
        
        # If user has specific skin type preferences, product must match
        if user_skin_types:
            # Check for overlap or if product supports "All" skin types
            return bool(user_skin_types.intersection(product_skin_types)) or 1 in product_skin_types  # 1 = "All"
        
        return True  # No restrictions
    
    def _check_allergen_safety(self, product: Dict) -> bool:
        """Check if product contains any allergens user wants to avoid"""
        excluded_ingredients = self.parsed_prefs["excluded_ingredients"]
        if not excluded_ingredients:
            return True
        
        product_ingredients = product.get("contents", "").lower()
        active_content = product.get("activeContent", "").lower()
        all_product_content = f"{product_ingredients} {active_content}"
        
        # Use the robust allergen detector
        return default_detector.is_safe_for_user(all_product_content, excluded_ingredients)
    
    def _check_age_appropriateness(self, product: Dict) -> bool:
        """Check if product is age-appropriate for the user"""
        user_age_range = self.parsed_prefs.get("age_range_preference")
        if not user_age_range:
            return True  # No age restrictions
        
        # Get product age recommendations (if any)
        product_description = product.get("description", "").lower()
        product_name = product.get("name", "").lower()
        product_benefits = product.get("keyBenefits", "").lower()
        
        all_product_text = f"{product_description} {product_name} {product_benefits}"
        
        # Age-based product filtering logic
        if user_age_range in ["SixteenPlus", "Twenties"]:
            # Young users: avoid heavy anti-aging products
            anti_aging_terms = ["anti-aging", "wrinkle", "firming", "lifting", "mature skin", "50+"]
            if any(term in all_product_text for term in anti_aging_terms):
                return False
        elif user_age_range in ["FiftyPlus"]:
            # Older users: prefer products with age-appropriate benefits
            # Allow all products but scoring will favor age-appropriate ones
            pass
        
        return True
    
    def _apply_high_priority_scoring(self, products: List[Dict]) -> List[Dict]:
        """Apply high priority filters and calculate initial scores"""
        scored_products = []
        
        for product in products:
            product_copy = product.copy()
            score = 0
            score_details = {"breakdown": {}}
            
            # Score skin concerns (HIGH priority)
            concern_score = self._score_skin_concerns(product)
            score += concern_score * 3  # High weight for concerns
            score_details["breakdown"]["skin_concerns"] = concern_score
            
            # Score skin tone compatibility (HIGH priority)
            skin_tone_score = self._score_skin_tone_compatibility(product)
            score += skin_tone_score * 2  # High weight for skin tone
            score_details["breakdown"]["skin_tone"] = skin_tone_score
            
            # Score age appropriateness (HIGH priority)
            age_score = self._score_age_appropriateness(product)
            score += age_score * 2  # High weight for age compatibility
            score_details["breakdown"]["age_appropriateness"] = age_score
            
            product_copy["score"] = score
            product_copy["score_details"] = score_details
            scored_products.append(product_copy)
        
        return scored_products
    
    def _apply_additional_scoring(self, products: List[Dict]) -> List[Dict]:
        """Apply medium and low priority scoring"""
        for product in products:
            current_score = product.get("score", 0)
            score_details = product.get("score_details", {"breakdown": {}})
            
            # Score fragrance preferences (MEDIUM priority)
            fragrance_score = self._score_fragrance_preferences(product)
            current_score += fragrance_score * 1  # Medium weight
            score_details["breakdown"]["fragrance"] = fragrance_score
            
            # Score shopping preferences (MEDIUM priority)
            shopping_score = self._score_shopping_preferences(product)
            current_score += shopping_score * 1  # Medium weight
            score_details["breakdown"]["shopping"] = shopping_score
            
            # Score hair compatibility (MEDIUM priority - for hair products)
            hair_score = self._score_hair_compatibility(product)
            current_score += hair_score * 1  # Medium weight
            score_details["breakdown"]["hair"] = hair_score
            
            # Score eye color compatibility (LOW priority)
            eye_score = self._score_eye_color_compatibility(product)
            current_score += eye_score * 0.5  # Low weight
            score_details["breakdown"]["eye_color"] = eye_score
            
            product["total_score"] = current_score
            product["score_details"] = score_details
        
        # Format output to only include name and id
        formatted_products = []
        for product in products:
            formatted_products.append({
                "name": product.get("name", ""),
                "id": product.get("id", ""),
                "total_score": product.get("total_score", 0)
            })
        
        return formatted_products
    
    def _score_skin_concerns(self, product: Dict) -> float:
        """Score based on how well product addresses user's skin concerns"""
        user_concerns = self.parsed_prefs["product_concerns"]
        if not user_concerns:
            return 0
        
        product_concerns = set(product.get("concerns", []))
        
        # Calculate overlap score
        overlap = user_concerns.intersection(product_concerns)
        return len(overlap) / len(user_concerns) if user_concerns else 0
    
    def _score_skin_tone_compatibility(self, product: Dict) -> float:
        """Score based on skin tone compatibility"""
        user_skin_tone = self.parsed_prefs.get("skin_tone_preference")
        if not user_skin_tone:
            return 0  # No preference, no bonus points
        
        product_name = product.get("name", "").lower()
        product_description = product.get("description", "").lower()
        product_benefits = product.get("keyBenefits", "").lower()
        all_text = f"{product_name} {product_description} {product_benefits}"
        
        # Skin tone compatibility mapping
        tone_keywords = {
            "Fair": ["fair", "light", "pale", "porcelain"],
            "FairLight": ["fair", "light", "pale"],
            "Light": ["light", "fair"],
            "LightMedium": ["light medium", "medium light", "light", "medium"],
            "Medium": ["medium", "neutral"],
            "MediumTan": ["medium tan", "tan", "medium"],
            "Tan": ["tan", "medium", "warm"],
            "Deep": ["deep", "dark", "rich"],
            "Rich": ["rich", "deep", "dark"],
            "NotSure": []  # No specific keywords
        }
        
        keywords = tone_keywords.get(user_skin_tone, [])
        if not keywords:
            return 0  # No specific skin tone preference
        
        # Score based on keyword matches
        matches = sum(1 for keyword in keywords if keyword in all_text)
        return min(matches / 2, 1.0)  # Cap at 1.0
    
    def _score_age_appropriateness(self, product: Dict) -> float:
        """Score based on age appropriateness and benefits"""
        user_age_range = self.parsed_prefs.get("age_range_preference")
        if not user_age_range:
            return 0
        
        product_name = product.get("name", "").lower()
        product_description = product.get("description", "").lower()
        product_benefits = product.get("keyBenefits", "").lower()
        all_text = f"{product_name} {product_description} {product_benefits}"
        
        # Age-appropriate keywords
        age_keywords = {
            "SixteenPlus": ["teen", "young", "gentle", "mild", "acne", "oil control"],
            "Twenties": ["hydrating", "preventive", "gentle", "daily", "protection"],
            "Thirties": ["anti-aging", "preventive", "hydrating", "firming", "protection"],
            "Forties": ["anti-aging", "firming", "lifting", "wrinkle", "mature", "intensive"],
            "FiftyPlus": ["anti-aging", "firming", "lifting", "wrinkle", "mature", "intensive", "renewal"]
        }
        
        keywords = age_keywords.get(user_age_range, [])
        if not keywords:
            return 0
        
        # Score based on keyword matches
        matches = sum(1 for keyword in keywords if keyword in all_text)
        return min(matches / 3, 1.0)  # Cap at 1.0
    
    def _score_fragrance_preferences(self, product: Dict) -> float:
        """Score based on fragrance preferences"""
        fragrance_prefs = self.parsed_prefs.get("medium_priority_filters", {}).get("fragrancePreferences", [])
        if not fragrance_prefs:
            return 0
        
        # This is a basic implementation - could be enhanced with more detailed matching
        return 0.5  # Basic score for having fragrance preferences
    
    def _score_shopping_preferences(self, product: Dict) -> float:
        """Score based on shopping preferences like luxury, BIPOC-owned, etc."""
        shopping_prefs = self.parsed_prefs.get("medium_priority_filters", {}).get("shoppingPreferences", [])
        if not shopping_prefs:
            return 0
        
        # This is a basic implementation - would need product metadata to properly implement
        return 0.3  # Basic score for shopping preferences
    
    def _score_hair_compatibility(self, product: Dict) -> float:
        """Score hair products based on hair type and concerns"""
        hair_type_prefs = self.parsed_prefs.get("medium_priority_filters", {}).get("hairType", [])
        if not hair_type_prefs:
            return 0
        
        # Check if this is a hair product
        product_name = product.get("name", "").lower()
        product_description = product.get("description", "").lower()
        
        hair_indicators = ["shampoo", "conditioner", "hair", "scalp", "styling"]
        if any(indicator in f"{product_name} {product_description}" for indicator in hair_indicators):
            return 0.5  # Basic score for hair product compatibility
        
        return 0
    
    def _score_eye_color_compatibility(self, product: Dict) -> float:
        """Score makeup products based on eye color compatibility"""
        eye_color = self.parsed_prefs.get("low_priority_filters", {}).get("eyeColor")
        if not eye_color:
            return 0
        
        # Check if this is an eye makeup product
        product_name = product.get("name", "").lower()
        product_description = product.get("description", "").lower()
        
        eye_indicators = ["eyeshadow", "eyeliner", "mascara", "eye"]
        if any(indicator in f"{product_name} {product_description}" for indicator in eye_indicators):
            return 0.3  # Basic score for eye makeup compatibility
        
        return 0
    
    def _get_applied_filters_summary(self) -> Dict:
        """Get summary of filters that were applied"""
        return {
            "critical_filters": list(self.parsed_prefs.get("critical_filters", {}).keys()),
            "high_priority_filters": list(self.parsed_prefs.get("high_priority_filters", {}).keys()),
            "excluded_ingredients_count": len(self.parsed_prefs.get("excluded_ingredients", [])),
            "skin_tone_preference": self.parsed_prefs.get("skin_tone_preference"),
            "age_range_preference": self.parsed_prefs.get("age_range_preference")
        }


def filter_products_by_user_preferences(user_preferences: Dict, products_data: Dict, max_products: int = 20) -> List[str]:
    """
    Standalone function to filter products by user preferences for backend integration
    
    Args:
        user_preferences: User preferences data from API
        products_data: Products data from API (dict with 'products' key)
        max_products: Maximum number of products to return
    
    Returns:
        List of product IDs: [product_ids]
    """
    try:
        engine = PreferenceRecommendationEngine(products_data, user_preferences)
        recommendations = engine.get_recommendations(max_products)
        
        if recommendations["success"]:
            # Extract only product IDs
            product_ids = [str(product["id"]) for product in recommendations["recommendations"]]
            return product_ids
        else:
            return []
            
    except Exception as e:
        print(f"Error in preference filtering: {e}")
        return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Get beauty product recommendations')
    parser.add_argument('--user-prefs', default='user_pref.json', 
                        help='Path to user preferences JSON file')
    parser.add_argument('--products', default='products.json',
                        help='Path to products JSON file')
    parser.add_argument('--max-products', type=int, default=20,
                        help='Maximum number of products to recommend')
    
    args = parser.parse_args()
    
    try:
        # Legacy file-based usage for testing
        with open(args.products, 'r') as f:
            products_data = json.load(f)
        with open(args.user_prefs, 'r') as f:
            user_prefs_data = json.load(f)
            
        results = filter_products_by_user_preferences(user_prefs_data, products_data, args.max_products)
        
        if results:
            print(f"\nFound {len(results)} recommendations")
            print(f"Product IDs: {results}")
        else:
            print("No recommendations found")
            
    except Exception as e:
        print(f"Error: {e}")