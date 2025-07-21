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
            else:
                skin_profile_parts.append(f"{skin_type} skin type")

    # Handle skin concerns
    if "skinConcerns" in user_preferences and user_preferences["skinConcerns"]:
        concerns = []
        for concern_id in user_preferences["skinConcerns"]:
            concern = get_mapped_value("skinConcerns", concern_id)
            if concern:
                if concern == "Rosacea":
                    concerns.append("rosacea, a condition characterized by persistent redness, flushing, and bumps")
                else:
                    concerns.append(concern.lower())
        
        if concerns:
            skin_profile_parts.append(f"Treating {', '.join(concerns)}")
    
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

    # Assemble the final document
    sections = []
    
    if skin_profile_parts:
        sections.append(f"[Skin Profile]. {'. '.join(skin_profile_parts)}.")
    
    if hair_profile_parts:
        sections.append(f"[Hair Profile]. {'. '.join(hair_profile_parts)}.")
    
    if preference_parts:
        sections.append(f"[Preferences]. {'. '.join(preference_parts)}.")
    
    return "\n\n".join(sections)