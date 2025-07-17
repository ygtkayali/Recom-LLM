"""
Robust allergen detection system with dynamic search term generation
"""
import re
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class AllergenPattern:
    """Represents an allergen detection pattern"""
    primary_terms: List[str]
    alternative_names: List[str] = None
    scientific_names: List[str] = None
    
    def __post_init__(self):
        if self.alternative_names is None:
            self.alternative_names = []
        if self.scientific_names is None:
            self.scientific_names = []


class AllergenDetector:
    """Advanced allergen detection with pattern-based search term generation"""
    
    def __init__(self):
        # Enhanced pattern database - easily extensible
        self.known_patterns = {
            # Fragrances & Perfumes
            "fragranceparfum": AllergenPattern(
                primary_terms=["fragrance", "parfum", "perfume"],
                alternative_names=["scent", "aroma"]
            ),
            "fragrancesandperfumes": AllergenPattern(
                primary_terms=["fragrance", "parfum", "perfume"],
                alternative_names=["scent", "aroma"]
            ),
            
            # Essential Oils (pattern-based)
            "teatreeoil": AllergenPattern(
                primary_terms=["tea tree", "tea tree oil"],
                scientific_names=["melaleuca alternifolia", "melaleuca"],
                alternative_names=["ti tree"]
            ),
            "lavenderoil": AllergenPattern(
                primary_terms=["lavender", "lavender oil"],
                scientific_names=["lavandula", "lavandula angustifolia"]
            ),
            "peppermintoil": AllergenPattern(
                primary_terms=["peppermint", "peppermint oil"],
                scientific_names=["mentha piperita", "mentha"]
            ),
            "eucalyptusoil": AllergenPattern(
                primary_terms=["eucalyptus", "eucalyptus oil"]
            ),
            "lemonoil": AllergenPattern(
                primary_terms=["lemon oil"],
                scientific_names=["citrus limon"]
            ),
            "limeoil": AllergenPattern(
                primary_terms=["lime oil"],
                scientific_names=["citrus aurantifolia"]
            ),
            "orangeoil": AllergenPattern(
                primary_terms=["orange oil"],
                scientific_names=["citrus aurantium", "citrus sinensis"]
            ),
            
            # Parabens (pattern-based)
            "methylparaben": AllergenPattern(
                primary_terms=["methylparaben", "methyl paraben"],
                alternative_names=["methyl 4-hydroxybenzoate"]
            ),
            "propylparaben": AllergenPattern(
                primary_terms=["propylparaben", "propyl paraben"],
                alternative_names=["propyl 4-hydroxybenzoate"]
            ),
            
            # Alcohols
            "sdalcohol": AllergenPattern(
                primary_terms=["sd alcohol", "alcohol denat"],
                alternative_names=["denatured alcohol", "ethyl alcohol"]
            ),
            "benzylalcohol": AllergenPattern(
                primary_terms=["benzyl alcohol"]
            ),
            
            # Acids
            "salicylicacid": AllergenPattern(
                primary_terms=["salicylic acid"],
                alternative_names=["bha", "beta hydroxy acid"]
            ),
            "glycolicacid": AllergenPattern(
                primary_terms=["glycolic acid"],
                alternative_names=["aha"]
            ),
            "lacticacid": AllergenPattern(
                primary_terms=["lactic acid"],
                alternative_names=["aha"]
            ),
            "alphahydroxyacids": AllergenPattern(
                primary_terms=["aha", "alpha hydroxy acid"],
                alternative_names=["glycolic acid", "lactic acid", "citric acid"]
            ),
            
            # Surfactants
            "sodiumlaurylsulfate": AllergenPattern(
                primary_terms=["sodium lauryl sulfate"],
                alternative_names=["sls", "sodium dodecyl sulfate"]
            ),
            "cocamidopropylbetaine": AllergenPattern(
                primary_terms=["cocamidopropyl betaine"],
                alternative_names=["capb"]
            ),
            
            # Other specific ingredients
            "dmdmhydantoin": AllergenPattern(
                primary_terms=["dmdm hydantoin"],
                alternative_names=["dimethylol dimethyl hydantoin"]
            ),
            "quaternium15": AllergenPattern(
                primary_terms=["quaternium-15", "quaternium 15"],
                alternative_names=["quaternium 15"]
            ),
            "witchhazel": AllergenPattern(
                primary_terms=["witch hazel"],
                scientific_names=["hamamelis", "hamamelis virginiana"]
            ),
            "beeswax": AllergenPattern(
                primary_terms=["beeswax"],
                alternative_names=["cera alba", "white wax"]
            ),
            
            # Nuts and botanical oils
            "almondoil": AllergenPattern(
                primary_terms=["almond oil"],
                scientific_names=["prunus amygdalus", "prunus dulcis"],
                alternative_names=["sweet almond oil"]
            ),
            "peanutoil": AllergenPattern(
                primary_terms=["peanut oil"],
                scientific_names=["arachis hypogaea"],
                alternative_names=["groundnut oil"]
            ),
            "coconutoil": AllergenPattern(
                primary_terms=["coconut oil"],
                scientific_names=["cocos nucifera"]
            ),
            
            # Category-level allergens
            "preservatives": AllergenPattern(
                primary_terms=["paraben", "phenoxyethanol", "benzyl alcohol"],
                alternative_names=["preservative", "antimicrobial"]
            ),
            "sunscreenagents": AllergenPattern(
                primary_terms=["titanium dioxide", "zinc oxide", "octinoxate", "avobenzone"],
                alternative_names=["uv filter", "sunscreen", "sun protection"]
            ),
            "essentialoils": AllergenPattern(
                primary_terms=["essential oil"],
                alternative_names=["parfum", "fragrance", "natural fragrance"]
            )
        }
    
    def generate_search_terms(self, allergen_name: str) -> List[str]:
        """Generate comprehensive search terms for an allergen"""
        allergen_key = allergen_name.lower()
        
        # Check if we have a known pattern
        if allergen_key in self.known_patterns:
            pattern = self.known_patterns[allergen_key]
            terms = []
            terms.extend(pattern.primary_terms)
            terms.extend(pattern.alternative_names)
            terms.extend(pattern.scientific_names)
            return list(set(terms))  # Remove duplicates
        
        # Fallback: generate terms using pattern analysis
        return self._generate_fallback_terms(allergen_name)
    
    def _generate_fallback_terms(self, allergen_name: str) -> List[str]:
        """Generate search terms for unknown allergens using pattern analysis"""
        terms = []
        base_name = allergen_name.lower()
        terms.append(base_name)
        
        # Handle CamelCase -> space separated
        spaced_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', allergen_name).lower()
        if spaced_name != base_name and len(spaced_name) > len(base_name):
            terms.append(spaced_name)
        
        # Handle common patterns
        patterns = {
            'oil': lambda x: [x[:-3].strip(), f"{x[:-3].strip()} oil"],
            'acid': lambda x: [x[:-4].strip(), f"{x[:-4].strip()} acid"],
            'paraben': lambda x: [x[:-7].strip(), f"{x[:-7].strip()} paraben"],
            'alcohol': lambda x: [x[:-7].strip(), f"{x[:-7].strip()} alcohol"]
        }
        
        for suffix, generator in patterns.items():
            if base_name.endswith(suffix) and len(base_name) > len(suffix) + 2:
                terms.extend(generator(base_name))
        
        return list(set(terms))
    
    def detect_allergens(self, product_content: str, excluded_allergens: List[str]) -> List[str]:
        """Detect which allergens are present in product content"""
        content_lower = product_content.lower()
        detected = []
        
        for allergen in excluded_allergens:
            search_terms = self.generate_search_terms(allergen)
            
            for term in search_terms:
                if term in content_lower:
                    detected.append(allergen)
                    break  # Found this allergen, move to next
        
        return detected
    
    def is_safe_for_user(self, product_content: str, excluded_allergens: List[str]) -> bool:
        """Check if product is safe (contains no excluded allergens)"""
        return len(self.detect_allergens(product_content, excluded_allergens)) == 0
    
    def add_custom_pattern(self, allergen_name: str, pattern: AllergenPattern):
        """Add a custom allergen pattern (for extensibility)"""
        self.known_patterns[allergen_name.lower()] = pattern
    
    def get_supported_allergens(self) -> List[str]:
        """Get list of allergens with enhanced detection patterns"""
        return list(self.known_patterns.keys())


# Singleton instance for easy import
default_detector = AllergenDetector()
