import sys
import os
from typing import Dict, Any

# Add parent directory to path to import mapping module
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from mapping import (
    BeautyPreferencesSkinConcern, BeautyPreferencesSkinTone, HairColor, 
    HairConcernsAndBenefits, AllergenicIngredients, BeautyPreferencesSkinType, 
    ShoppingPreferences, FragrancePreferences, HairType, EyeColor, AgeRange,
    PREFERENCE_PRIORITY
)

# Create a mapping dictionary for all categories
ALL_MAPPINGS = {
    "skinType": BeautyPreferencesSkinType,
    "skinConcerns": BeautyPreferencesSkinConcern,
    "skinTone": BeautyPreferencesSkinTone,
    "allergenicIngredients": AllergenicIngredients,
    "fragrancePreferences": FragrancePreferences,
    "hairType": HairType,
    "hairColor": HairColor,
    "hairConcernsAndBenefits": HairConcernsAndBenefits,
    "shoppingPreferences": ShoppingPreferences,
    "eyeColor": EyeColor,
    "ageRange": AgeRange,
}

def create_user_profile_document(user_preferences: Dict[str, Any]) -> str:
    """
    Translates a user's preference JSON into a rich, natural-language string
    ready for embedding, formatted in sections like [Skin Profile], [Hair Profile], [Preferences].

    Args:
        user_preferences: The raw JSON object of user preferences.

    Returns:
        A single string describing the user's complete profile.
    """
    
    def get_mapped_value(category: str, key: Any) -> str:
        """Helper to safely get a value from the mappings."""
        return ALL_MAPPINGS.get(category, {}).get(key, "")

    # Organize content by profile sections
    skin_profile_parts = []
    hair_profile_parts = []
    preference_parts = []

    # Handle skin type
    if "skinType" in user_preferences and user_preferences["skinType"]:
        skin_type = get_mapped_value("skinType", user_preferences["skinType"])
        if skin_type:
            if skin_type == "Sensitive":
                skin_profile_parts.append("Sensitive skin type, which is prone to irritation, redness, and reactions")
            elif skin_type == "Dry":
                skin_profile_parts.append("Dry skin type, which may feel tight and rough")
            elif skin_type == "Oily":
                skin_profile_parts.append("Oily skin type, which may appear shiny and prone to acne")
            elif skin_type == "Combination":
                skin_profile_parts.append("Combination skin type, which has both oily and dry areas")
            elif skin_type == "Normal":
                skin_profile_parts.append("Normal skin type, which is balanced and not prone to dryness or oiliness")
            else:
                skin_profile_parts.append(f"{skin_type} skin type")
            
    if "skinTone" in user_preferences and user_preferences["skinTone"]:
        skin_tone = get_mapped_value("skinTone", user_preferences["skinTone"])
        if skin_tone:
            skin_profile_parts.append(f"Skin tone is {skin_tone.lower()}")
    
    if "hairType" in user_preferences and user_preferences["hairType"]:
        hair_type = get_mapped_value("hairType", user_preferences["hairType"][0])
        if hair_type:
            hair_profile_parts.append(f"Hair type is {hair_type.lower()}")
    
    if "hairColor" in user_preferences and user_preferences["hairColor"]:
        hair_color = get_mapped_value("hairColor", user_preferences["hairColor"][0])
        if hair_color:
            hair_profile_parts.append(f"Hair color is {hair_color.lower()}")
    
    
    # Handle hair concerns and benefits
    if "hairConcernsAndBenefits" in user_preferences and user_preferences["hairConcernsAndBenefits"]:
        hair_goals = []
        for goal_id in user_preferences["hairConcernsAndBenefits"]:
            goal = get_mapped_value("hairConcernsAndBenefits", goal_id)
            if goal:
                if goal == "Shine":
                    hair_goals.append("improve hair shine and radiance")
                elif goal == "Volumizing":
                    hair_goals.append("add volume and body to hair")
                elif goal == "HeatProtection":
                    hair_goals.append("get heat protection from styling tools")
                elif goal == "ColorSafe" or goal == "ColorFading":
                    hair_goals.append("get color protection for color-treated hair")
                else:
                    hair_goals.append(f"improve {goal.lower()}")
        
        if hair_goals:
            for goal in hair_goals:
                hair_profile_parts.append(f"Wants to {goal}")

    # Handle shopping preferences and allergies
    if "shoppingPreferences" in user_preferences and user_preferences["shoppingPreferences"]:
        shop_prefs = []
        for pref_id in user_preferences["shoppingPreferences"]:
            pref = get_mapped_value("shoppingPreferences", pref_id)
            if pref:
                if "Luxury" in pref:
                    shop_prefs.append("luxury products")
                elif pref == "PlanetAware":
                    shop_prefs.append("clean beauty products, formulated without ingredients like sulfates and parabens")
                else:
                    shop_prefs.append(pref.lower())
        
        if shop_prefs:
            preference_parts.append(f"Prefers {', '.join(shop_prefs)}")

    # Handle allergenic ingredients
    if "allergenicIngredients" in user_preferences and user_preferences["allergenicIngredients"]:
        allergies = []
        for allergy_id in user_preferences["allergenicIngredients"]:
            allergy = get_mapped_value("allergenicIngredients", allergy_id)
            if allergy:
                if "paraben" in allergy.lower():
                    allergies.append("parabens")
                elif allergy == "FragrancesAndPerfumes":
                    allergies.append("fragrances")
                else:
                    allergies.append(allergy.lower())
        
        if allergies:
            preference_parts.append(f"Allergic to {', '.join(set(allergies))}")  # Use set to remove duplicates
    if "fragrancePreferences" in user_preferences and user_preferences["fragrancePreferences"]:
        fragrance_prefs = []
        for pref_id in user_preferences["fragrancePreferences"]:
            pref = get_mapped_value("fragrancePreferences", pref_id)
            if pref:
                fragrance_prefs.append(pref.lower())
        
        if fragrance_prefs:
            preference_parts.append(f"Prefers fragrances like {', '.join(fragrance_prefs)}")
    
    if "ageRange" in user_preferences and user_preferences["ageRange"]:
        age_range = get_mapped_value("ageRange", user_preferences["ageRange"])
        if age_range:
            preference_parts.append(f"Age range is {age_range.lower()}")
    
    if "eyeColor" in user_preferences and user_preferences["eyeColor"]:
        eye_color = get_mapped_value("eyeColor", user_preferences["eyeColor"])
        if eye_color:
            preference_parts.append(f"Eye color is {eye_color.lower()}")
    
    # Assemble the final document
    sections = []
    
    if skin_profile_parts:
        sections.append(f"[Skin Profile]. {'. '.join(skin_profile_parts)}.")
    
    if hair_profile_parts:
        sections.append(f"[Hair Profile]. {'. '.join(hair_profile_parts)}.")
    
    if preference_parts:
        sections.append(f"[Preferences]. {'. '.join(preference_parts)}.")
    
    return "\n\n".join(sections)