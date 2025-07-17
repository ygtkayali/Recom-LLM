BeautyPreferencesSkinType = {
    1: "Combination",
    2: "Dry", 
    3: "Normal",
    4: "Oily",
    5: "Sensitive",
    6: "DryAndSensitive",
    7: "OilAndSensitive", 
    8: "CombinationSensitive"
}

BeautyPreferencesSkinConcern = {
    1: "AcneBlemishes",
    2: "Moisture",
    3: "Pores",
    4: "FineLinesWrinkles",
    5: "DarkCircles",
    6: "Redness",
    7: "Oiliness",
    8: "Dryness",
    9: "Sensitivity",
    10: "UnevenSkinTone",
    11: "Texture",
    12: "FirmnessElasticity",
    13: "DarkSpotsHyperpigmentation",
    14: "DullnessRadiance",
    15: "Puffiness",
    16: "SunDamage",
    17: "LossOfVolume",
    18: "Cellulite",
    19: "StretchMarks",
    20: "KeratosisPilaris",
    21: "Eczema",
    22: "Rosacea"
}

BeautyPreferencesSkinTone = {
    0: "Rich",
    1: "Deep", 
    2: "Tan",
    3: "MediumTan",
    4: "Medium",
    5: "LightMedium",
    6: "Light",
    7: "Fair",
    8: "FairLight",
    9: "NotSure"
}

AllergenicIngredients = {
    # Main Categories
    1: "FragrancesAndPerfumes",
    2: "Preservatives", 
    3: "SunscreenAgents",
    4: "SurfactantsAndEmulsifiers",
    5: "ColorantsAndDyes",
    6: "PlantBasedAllergens",
    7: "AlcoholsAndAcids",
    8: "AnimalDerivedIngredients",
    9: "OtherCommonAllergens",
    
    # Fragrances & Perfumes
    100: "FragranceParfum",
    101: "Linalool",
    102: "Citronellol", 
    103: "Geraniol",
    104: "Eugenol",
    105: "Cinnamal",
    106: "Hydroxycitronellal",
    
    # Preservatives
    107: "Methylparaben",
    108: "Propylparaben",
    109: "DMDMHydantoin",
    110: "ImidazolidinylUrea",
    111: "Quaternium15",
    112: "Phenoxyethanol",
    113: "Methylisothiazolinone",
    114: "Methylchloroisothiazolinone",
    115: "BenzylAlcohol",
    116: "Formaldehyde",
    
    # Sunscreen Agents
    117: "Oxybenzone",
    118: "Avobenzone",
    119: "Octinoxate",
    120: "Homosalate",
    121: "PABA",
    
    # Surfactants/Emulsifiers
    122: "CocamidopropylBetaine",
    123: "SodiumLaurylSulfate",
    124: "Polysorbates",
    125: "AmmoniumLaurylSulfate",
    
    # Colorants & Dyes
    126: "FDCRed40",
    127: "FDCYellow5",
    128: "CoalTarDyes",
    129: "Chromium",
    130: "Cobalt",
    
    # Plant-Based Allergens
    131: "TeaTreeOil",
    132: "LavenderOil",
    133: "PeppermintOil",
    134: "EucalyptusOil",
    135: "LemonOil",
    136: "LimeOil",
    137: "OrangeOil",
    138: "Arnica",
    139: "WitchHazel",
    
    # Alcohols and Acids
    140: "SDAlcohol",
    141: "AlphaHydroxyAcids",
    142: "SalicylicAcid",
    143: "GlycolicAcid",
    144: "LacticAcid",
    
    # Animal-Derived Ingredients
    145: "Lanolin",
    146: "Beeswax",
    
    # Other Common Allergens
    147: "AlmondOil",
    148: "PeanutOil",
    149: "CoconutOil",
    150: "Nickel",
    151: "Latex",
    152: "EssentialOils"
}

FragrancePreferences = {
    1: "FloralMist",
    2: "WoodyAndEarthy", 
    3: "WarmAndSpicy",
    4: "FreshFruit"
}

HairType = {
    1: "Fine",
    2: "Medium",
    3: "Thick"
}

HairConcernsAndBenefits = {
    1: "Brassiness",
    2: "ColorFading",
    3: "ColorSafe",
    4: "CurlEnhancing",
    5: "DamageSplitEnds",
    6: "Dandruff",
    7: "Dryness",
    8: "FlakyDryScalp",
    9: "Frizz",
    10: "HeatProtection",
    11: "HoldAndStyleExtending",
    12: "OilyScalp",
    13: "ScalpBuildUp",
    14: "StraighteningSmoothing",
    15: "Shine",
    16: "Thinning",
    17: "UVProtection",
    18: "Volumizing"
}

HairColor = {
    1: "Black",
    2: "Brown", 
    3: "Blonde",
    4: "Auburn",
    5: "Red",
    6: "Gray"
}

ShoppingPreferences = {
    1: "BestOfAllure",
    2: "BIPOCOwnedBrands",
    3: "BlackOwnedBrands",
    4: "LuxuryFrangence",
    5: "LuxuryMakeup",
    6: "LuxurySkincare",
    7: "LuxuryHair",
    8: "OnlyAtSmartBeauty",
    9: "PlanetAware"
}

EyeColor = {
    1: "Brown",
    2: "Blue",
    3: "Green",
    4: "Gray",
    5: "Hazel"
}

AgeRange = {
    1: "SixteenPlus",
    2: "Twenties",
    3: "Thirties", 
    4: "Forties",
    5: "FiftyPlus"
}

# Preference Priority Levels
PREFERENCE_PRIORITY = {
    "CRITICAL": ["skinType", "allergenicIngredients","skinConcerns"],  # Must match
    "HIGH": ["skinTone", "ageRange"],  # Very important
    "MEDIUM": ["fragrancePreferences", "hairType", "shoppingPreferences"],  # Important
    "LOW": ["eyeColor", "hairColor", "favoriteBrands"]  # Nice to have
}

# Mapping between beauty preferences and existing product concerns/skin types
BEAUTY_TO_PRODUCT_MAPPING = {
    # Skin concerns mapping
    "AcneBlemishes": {"concerns": [5, 7], "skinTypes": [3, 4]},  # Blemish, Acne -> Oily, Combination
    "Moisture": {"concerns": [3], "skinTypes": [4]},             # Dryness -> Dry
    "Pores": {"concerns": [1], "skinTypes": [3, 4]},            # Pores -> Oily, Combination
    "FineLinesWrinkles": {"concerns": [0, 8], "skinTypes": []}, # Wrinkles, Aging
    "DarkCircles": {"concerns": [6], "skinTypes": []},          # EyeArea
    "Redness": {"concerns": [5], "skinTypes": [0]},             # Blemish -> Sensitive
    "Oiliness": {"concerns": [7], "skinTypes": [3]},            # Acne -> Oily
    "Dryness": {"concerns": [3], "skinTypes": [4]},             # Dryness -> Dry
    "UnevenSkinTone": {"concerns": [4, 9], "skinTypes": []},    # Unevenness, Spots
    "DullnessRadiance": {"concerns": [2], "skinTypes": []},     # Dullness
    # Add more mappings as needed
}

# Centralized special mappings for skin analysis - only for analysis types that don't directly match concern names
# or provide multiple concerns for a single analysis type
SPECIAL_MAPPINGS = {
    'eyebag': {'concerns': ['darkcircles', 'puffiness']},
    'wrinkle': {'concerns': ['finelineswrinkles', 'firmnesselasticity']},
    'acne': {'concerns': ['acneblemishes', 'oiliness']},
    'blemish': {'concerns': ['acneblemishes']},
    'darkspots': {'concerns': ['darkspotshyperpigmentation', 'unevenskintone']},
    'hydration': {'concerns': ['moisture', 'dryness']},
    'rosacea': {'concerns': ['rosacea', 'redness', 'sensitivity']},
}
