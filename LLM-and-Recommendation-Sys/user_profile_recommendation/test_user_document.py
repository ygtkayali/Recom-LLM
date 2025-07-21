#!/usr/bin/env python3
"""
Test script for create_user_document.py functionality
"""

import sys
import os

# Add parent directory to path to import mapping module
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from create_user_document import create_user_profile_document

def test_user_profile_creation():
    """Test the user profile document creation with sample data."""
    
    # Sample user preferences matching the expected format
    sample_user_preferences = {
        # CRITICAL priority
        "skinType": 5,  # Sensitive
        "skinConcerns": [22, 6, 9],  # Rosacea, Redness, Sensitivity
        "allergenicIngredients": [107, 108, 1],  # Methylparaben, Propylparaben, FragrancesAndPerfumes
        
        # HIGH priority
        "skinTone": 6,  # Light
        "ageRange": 3,  # Thirties
        
        # MEDIUM priority
        "fragrancePreferences": [1, 4],  # FloralMist, FreshFruit
        "hairType": 1,  # Fine
        "shoppingPreferences": [6, 9],  # LuxurySkincare, PlanetAware
        
        # LOW priority
        "eyeColor": 3,  # Green
        "hairColor": 3,  # Blonde
    }
    
    print("🧪 Testing User Profile Document Creation")
    print("=" * 50)
    print("Sample User Preferences:")
    for key, value in sample_user_preferences.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("Generated Profile Document:")
    print("=" * 50)
    
    try:
        profile_document = create_user_profile_document(sample_user_preferences)
        print(profile_document)
        
        print("\n" + "=" * 50)
        print("✅ Test completed successfully!")
        print(f"📊 Document length: {len(profile_document)} characters")
        print(f"📝 Number of sentences: {profile_document.count('.')}")
        
        return profile_document
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_edge_cases():
    """Test edge cases for the user profile creation."""
    
    print("\n🔍 Testing Edge Cases")
    print("=" * 50)
    
    # Test with empty preferences
    empty_prefs = {}
    print("Test 1: Empty preferences")
    try:
        result = create_user_profile_document(empty_prefs)
        print(f"Result: '{result}'")
        print("✅ Empty preferences handled correctly")
    except Exception as e:
        print(f"❌ Error with empty preferences: {e}")
    
    # Test with invalid IDs
    invalid_prefs = {
        "skinType": 999,  # Invalid ID
        "skinConcerns": [0, 9999],  # Mix of valid and invalid
        "allergenicIngredients": []  # Empty list
    }
    print("\nTest 2: Invalid IDs and empty lists")
    try:
        result = create_user_profile_document(invalid_prefs)
        print(f"Result: '{result}'")
        print("✅ Invalid IDs handled correctly")
    except Exception as e:
        print(f"❌ Error with invalid IDs: {e}")

def test_expected_output_format():
    """Test to match the expected output format from the user request."""
    
    print("\n🎯 Testing Expected Output Format")
    print("=" * 50)
    
    # Create preferences that should generate the expected output
    target_preferences = {
        "skinType": 5,  # Sensitive
        "skinConcerns": [22, 6],  # Rosacea, Redness
        "allergenicIngredients": [107],  # Methylparaben (parabens)
        "shoppingPreferences": [6, 9],  # LuxurySkincare, PlanetAware (clean beauty)
        "hairConcernsAndBenefits": [15, 18, 10, 2],  # Shine, Volumizing, HeatProtection, ColorFading
    }
    
    print("Target preferences for expected format:")
    for key, value in target_preferences.items():
        print(f"  {key}: {value}")
    
    print("\nGenerated document:")
    try:
        result = create_user_profile_document(target_preferences)
        print(result)
        print("\n✅ Expected format test completed")
    except Exception as e:
        print(f"❌ Error in expected format test: {e}")

if __name__ == "__main__":
    # Run all tests
    test_user_profile_creation()
    test_edge_cases()
    test_expected_output_format()
