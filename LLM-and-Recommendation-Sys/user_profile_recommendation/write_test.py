#!/usr/bin/env python3
"""
Test that writes output to file for clear viewing
"""

import sys
import os

# Add parent directory to path to import mapping module
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from create_user_document import create_user_profile_document

def main():
    # Test data that should produce the expected format
    test_preferences = {
        "skinType": 5,  # Sensitive
        "skinConcerns": [22, 6],  # Rosacea, Redness
        "allergenicIngredients": [107],  # Methylparaben (parabens)
        "shoppingPreferences": [9],  # PlanetAware (clean beauty)
        "hairConcernsAndBenefits": [15, 18, 10, 2],  # Shine, Volumizing, HeatProtection, ColorFading
    }
    
    result = create_user_profile_document(test_preferences)
    
    # Write to file
    with open("test_output.txt", "w") as f:
        f.write("=== USER PROFILE DOCUMENT ===\n")
        f.write(result)
        f.write("\n==============================\n")
    
    print("Output written to test_output.txt")
    print("First 200 characters:")
    print(result[:200] + "...")

if __name__ == "__main__":
    main()
