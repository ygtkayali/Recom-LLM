#!/usr/bin/env python3
"""
Simple test to show clean output
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
  "skinType": 4,
  "skinConcerns": [
    2,
    0,
    21,
    3
  ],
  "skinTone": 0,
  "colorIQ": 1,
  "allergenicIngredients": [
    122,
    100,
    104,
    145,
    124,
    105,
    140,
    102,
    110,
    113,
    123,
    115,
    125,
    114,
    109,
    106,
    112,
    146,
    101,
    116,
    103
  ],
  "fragrancePreferences": [
    3,
    4,
    2,
    1
  ],
  "hairType": [
    1,
    3
  ],
  "hairTexture": [
    1
  ],
  "hairConcernsAndBenefits": [
    16,
    18,
    2,
    4,
    17
  ],
  "hairColor": [
    3,
    2
  ],
  "shoppingPreferences": [
    9,
    5,
    8,
    1
  ],
  "favoriteBrands": [
    4,
    3,
    1,
    2
  ],}
    
    result = create_user_profile_document(test_preferences)
    print("=== USER PROFILE DOCUMENT ===")
    print(result)
    print("==============================")

if __name__ == "__main__":
    main()
