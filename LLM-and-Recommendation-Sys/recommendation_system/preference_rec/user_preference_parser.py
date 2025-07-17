import json
from typing import Dict, List, Set, Tuple
from ..mapping import (
    BeautyPreferencesSkinType,
    BeautyPreferencesSkinConcern,
    BeautyPreferencesSkinTone,
    AllergenicIngredients,
    FragrancePreferences,
    HairType,
    HairConcernsAndBenefits,
    HairColor,
    ShoppingPreferences,
    EyeColor,
    AgeRange,
    PREFERENCE_PRIORITY,
    BEAUTY_TO_PRODUCT_MAPPING
)

class UserPreferenceParser:
    def __init__(self, user_pref_path: str = None):
        """
        Initialize parser. Can work with file path (legacy) or data directly
        """
        if user_pref_path:
            with open(user_pref_path, 'r') as f:
                self.user_prefs = json.load(f)
        else:
            self.user_prefs = {}
    
    def parse_preferences_from_data(self, user_preferences_data: Dict) -> Dict[str, any]:
        """Parse user preferences from API data and convert to product search criteria"""
        self.user_prefs = user_preferences_data
        return self.parse_preferences()
    
    def parse_preferences(self) -> Dict[str, any]:
        """Parse user preferences and convert to product search criteria"""
        parsed = {
            "critical_filters": {},
            "high_priority_filters": {},
            "medium_priority_filters": {},
            "low_priority_filters": {},
            "excluded_ingredients": [],
            "product_concerns": set(),
            "product_skin_types": set(),
            "skin_tone_preference": None,
            "age_range_preference": None
        }
        
        # Parse skin type (CRITICAL)
        if self.user_prefs.get("skinType", 0) != 0:
            skin_type_name = BeautyPreferencesSkinType.get(self.user_prefs["skinType"])
            parsed["critical_filters"]["skinType"] = skin_type_name
            # Map to product skin types
            self._map_to_product_criteria(skin_type_name, parsed)
        
        # Parse skin concerns (HIGH)
        concerns = self.user_prefs.get("skinConcerns", [])
        if concerns and concerns != [0]:
            concern_names = [BeautyPreferencesSkinConcern.get(c) for c in concerns if c != 0]
            parsed["high_priority_filters"]["skinConcerns"] = concern_names
            # Map to product concerns
            for concern in concern_names:
                self._map_to_product_criteria(concern, parsed)
        
        # Parse skin tone (HIGH)
        if self.user_prefs.get("skinTone", 0) != 0:
            skin_tone_name = BeautyPreferencesSkinTone.get(self.user_prefs["skinTone"])
            parsed["high_priority_filters"]["skinTone"] = skin_tone_name
            parsed["skin_tone_preference"] = skin_tone_name
        
        # Parse age range (HIGH)
        if self.user_prefs.get("ageRange", 0) != 0:
            age_range_name = AgeRange.get(self.user_prefs["ageRange"])
            parsed["high_priority_filters"]["ageRange"] = age_range_name
            parsed["age_range_preference"] = age_range_name
        
        # Parse allergenic ingredients (CRITICAL)
        allergens = self.user_prefs.get("allergenicIngredients", [])
        if allergens and allergens != [0]:
            allergen_names = [AllergenicIngredients.get(a) for a in allergens if a != 0]
            parsed["critical_filters"]["allergenicIngredients"] = allergen_names
            parsed["excluded_ingredients"] = allergen_names
        
        # Parse fragrance preferences (MEDIUM)
        fragrances = self.user_prefs.get("fragrancePreferences", [])
        if fragrances and fragrances != [0]:
            fragrance_names = [FragrancePreferences.get(f) for f in fragrances if f != 0]
            parsed["medium_priority_filters"]["fragrancePreferences"] = fragrance_names
        
        # Parse hair type (MEDIUM)
        hair_types = self.user_prefs.get("hairType", [])
        if hair_types and hair_types != [0]:
            hair_type_names = [HairType.get(h) for h in hair_types if h != 0]
            parsed["medium_priority_filters"]["hairType"] = hair_type_names
        
        # Parse shopping preferences (MEDIUM)
        shopping = self.user_prefs.get("shoppingPreferences", [])
        if shopping and shopping != [0]:
            shopping_names = [ShoppingPreferences.get(s) for s in shopping if s != 0]
            parsed["medium_priority_filters"]["shoppingPreferences"] = shopping_names
        
        # Parse eye color (LOW)
        if self.user_prefs.get("eyeColor", 0) != 0:
            eye_color_name = EyeColor.get(self.user_prefs["eyeColor"])
            parsed["low_priority_filters"]["eyeColor"] = eye_color_name
        
        return parsed
    
    def _map_to_product_criteria(self, preference_name: str, parsed: Dict):
        """Map beauty preferences to existing product concerns/skin types"""
        if preference_name in BEAUTY_TO_PRODUCT_MAPPING:
            mapping = BEAUTY_TO_PRODUCT_MAPPING[preference_name]
            parsed["product_concerns"].update(mapping.get("concerns", []))
            parsed["product_skin_types"].update(mapping.get("skinTypes", []))