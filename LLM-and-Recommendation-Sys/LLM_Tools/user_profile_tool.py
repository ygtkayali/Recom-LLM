#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 25 20:38:02 2025

@author: ahmetselimyavuz
"""
"""
#!/usr/bin/env python


Usage:
from user_profile_tool import UserProfileTool

# Initialize for authenticated user
tool = UserProfileTool(authenticated_user_id=123)

# Update profile text (triggers embedding regeneration)
result = tool.update_profile_text("[Skin Profile]. Sensitive skin type...")

# Update specific profile sections
result = tool.update_profile_section("skin_concerns", ["acne", "rosacea"])
"""

import os
import sys
import re
import json
from typing import Union, Dict, Any, List, Optional
from datetime import datetime
import logging

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from db.connection import get_database_manager, test_db_connection
from user_profile_recommendation.create_user_document import create_user_profile_document


class UserProfileTool:
    """
    Secure user profile management tool for SmartBeauty database.
    
    This tool:
    - Only allows authenticated user to modify their own profile
    - Works with the actual database schema (users table)
    - Supports natural language profile updates
    - Automatically regenerates embeddings when profile changes
    - Provides comprehensive logging and error handling
    """
    
    def __init__(self, authenticated_user_id: int):
        """
        Initialize the UserProfileTool for a specific authenticated user.
        
        Args:
            authenticated_user_id: The ID of the currently authenticated user
        """
        self.authenticated_user_id = authenticated_user_id
        self.logger = logging.getLogger(__name__)
        
        # Verify database connection
        if not test_db_connection():
            raise ConnectionError("Database connection failed")
        
        # Verify user exists
        if not self._user_exists():
            raise ValueError(f"User with ID {authenticated_user_id} does not exist")
    
    def _user_exists(self) -> bool:
        """Check if the authenticated user exists in the database."""
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM users WHERE id = %s", (self.authenticated_user_id,))
                    return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Error checking user existence: {e}")
            return False
    
    def _invalidate_embedding(self) -> bool:
        """Set embedding to NULL so it gets regenerated."""
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET embedding = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (self.authenticated_user_id,))
                    conn.commit()
                    return True
        except Exception as e:
            self.logger.error(f"Error invalidating embedding: {e}")
            return False
    
    def update_profile_text(self, new_profile_text: str) -> Dict[str, Any]:
        """
        Update the user's complete profile text.
        
        Args:
            new_profile_text: New natural language profile text
            
        Returns:
            Dictionary with operation result
        """
        try:
            if not new_profile_text or not new_profile_text.strip():
                return {
                    "success": False,
                    "error": "Profile text cannot be empty"
                }
            
            # Sanitize input
            profile_text = new_profile_text.strip()
            
            # Validate length (reasonable limits)
            if len(profile_text) > 5000:
                return {
                    "success": False,
                    "error": "Profile text too long (max 5000 characters)"
                }
            
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET embedding_text = %s, embedding = NULL, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (profile_text, self.authenticated_user_id))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        return {
                            "success": True,
                            "message": "Profile text updated successfully",
                            "user_id": self.authenticated_user_id,
                            "characters": len(profile_text),
                            "embedding_invalidated": True
                        }
                    else:
                        return {
                            "success": False,
                            "error": "No rows updated"
                        }
        
        except Exception as e:
            self.logger.error(f"Error updating profile text: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }
    
    def update_profile_section(self, section_type: str, values: List[str]) -> Dict[str, Any]:
        """
        Update a specific section of the user profile using natural language generation.
        
        Args:
            section_type: Type of section ('skin_concerns', 'hair_goals', 'preferences', etc.)
            values: List of values for that section
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Get current profile
            current_profile = self.get_current_profile()
            if not current_profile["success"]:
                return current_profile
            
            # Parse current profile or create new structure
            profile_structure = self._parse_profile_to_structure(
                current_profile.get("profile_text", "")
            )
            
            # Update the specific section
            profile_structure = self._update_profile_structure(profile_structure, section_type, values)
            
            # Generate new natural language profile
            new_profile_text = self._generate_profile_from_structure(profile_structure)
            
            # Update the profile text
            return self.update_profile_text(new_profile_text)
        
        except Exception as e:
            self.logger.error(f"Error updating profile section: {e}")
            return {
                "success": False,
                "error": f"Section update error: {str(e)}"
            }
    
    def add_to_profile_section(self, section_type: str, new_values: List[str]) -> Dict[str, Any]:
        """
        Add new values to a specific profile section.
        
        Args:
            section_type: Type of section to add to
            new_values: List of new values to add
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Get current profile
            current_profile = self.get_current_profile()
            if not current_profile["success"]:
                return current_profile
            
            # Parse current profile
            profile_structure = self._parse_profile_to_structure(
                current_profile.get("profile_text", "")
            )
            
            # Add to existing values
            if section_type in profile_structure:
                existing_values = profile_structure[section_type]
                combined_values = list(set(existing_values + new_values))  # Remove duplicates
            else:
                combined_values = new_values
            
            # Update section
            return self.update_profile_section(section_type, combined_values)
        
        except Exception as e:
            self.logger.error(f"Error adding to profile section: {e}")
            return {
                "success": False,
                "error": f"Add operation error: {str(e)}"
            }
    
    def remove_from_profile_section(self, section_type: str, values_to_remove: List[str]) -> Dict[str, Any]:
        """
        Remove values from a specific profile section.
        
        Args:
            section_type: Type of section to remove from
            values_to_remove: List of values to remove
            
        Returns:
            Dictionary with operation result
        """
        try:
            # Get current profile
            current_profile = self.get_current_profile()
            if not current_profile["success"]:
                return current_profile
            
            # Parse current profile
            profile_structure = self._parse_profile_to_structure(
                current_profile.get("profile_text", "")
            )
            
            # Remove values
            if section_type in profile_structure:
                existing_values = profile_structure[section_type]
                updated_values = [v for v in existing_values if v not in values_to_remove]
                
                # Update section
                return self.update_profile_section(section_type, updated_values)
            else:
                return {
                    "success": False,
                    "error": f"Section '{section_type}' not found in profile"
                }
        
        except Exception as e:
            self.logger.error(f"Error removing from profile section: {e}")
            return {
                "success": False,
                "error": f"Remove operation error: {str(e)}"
            }
    
    def get_current_profile(self) -> Dict[str, Any]:
        """
        Get the current user profile information.
        
        Returns:
            Dictionary with current profile data
        """
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT embedding_text, embedding, created_at, updated_at
                        FROM users
                        WHERE id = %s
                    """, (self.authenticated_user_id,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        embedding_text, embedding, created_at, updated_at = result
                        return {
                            "success": True,
                            "user_id": self.authenticated_user_id,
                            "profile_text": embedding_text,
                            "has_embedding": embedding is not None,
                            "created_at": created_at.isoformat() if created_at else None,
                            "updated_at": updated_at.isoformat() if updated_at else None,
                            "character_count": len(embedding_text) if embedding_text else 0
                        }
                    else:
                        return {
                            "success": False,
                            "error": "User profile not found"
                        }
        
        except Exception as e:
            self.logger.error(f"Error getting current profile: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }
    
    def _parse_profile_to_structure(self, profile_text: str) -> Dict[str, List[str]]:
        """
        Parse natural language profile text into structured data.
        
        This is a simplified parser - in production you might want more sophisticated NLP.
        
        Args:
            profile_text: Natural language profile text
            
        Returns:
            Dictionary with structured profile data
        """
        structure = {
            "skin_type": [],
            "skin_concerns": [],
            "hair_goals": [],
            "preferences": [],
            "allergies": []
        }
        
        if not profile_text:
            return structure
        
        # Simple regex-based parsing of the profile sections
        # This matches the format created by create_user_profile_document
        
        # Extract skin concerns
        skin_match = re.search(r'\[Skin Profile\]\.\s*(.*?)(?:\[|$)', profile_text, re.DOTALL)
        if skin_match:
            skin_text = skin_match.group(1)
            # Extract skin type
            if "skin type" in skin_text.lower():
                structure["skin_type"].append(skin_text.split('.')[0].strip())
            # Extract concerns (simplified)
            if "treating" in skin_text.lower():
                concerns = re.findall(r'treating ([^.,]+)', skin_text.lower())
                structure["skin_concerns"].extend(concerns)
        
        # Extract hair goals
        hair_match = re.search(r'\[Hair Profile\]\.\s*(.*?)(?:\[|$)', profile_text, re.DOTALL)
        if hair_match:
            hair_text = hair_match.group(1)
            goals = re.findall(r'wants to ([^.]+)', hair_text.lower())
            structure["hair_goals"].extend(goals)
        
        # Extract preferences and allergies
        pref_match = re.search(r'\[Preferences\]\.\s*(.*?)(?:\[|$)', profile_text, re.DOTALL)
        if pref_match:
            pref_text = pref_match.group(1)
            # Extract preferences
            prefs = re.findall(r'prefers ([^.]+)', pref_text.lower())
            structure["preferences"].extend(prefs)
            # Extract allergies
            allergies = re.findall(r'allergic to ([^.]+)', pref_text.lower())
            structure["allergies"].extend(allergies)
        
        return structure
    
    def _update_profile_structure(self, structure: Dict[str, List[str]], section_type: str, values: List[str]) -> Dict[str, List[str]]:
        """Update a specific section in the profile structure."""
        if section_type in structure:
            structure[section_type] = values
        else:
            self.logger.warning(f"Unknown section type: {section_type}")
        
        return structure
    
    def _generate_profile_from_structure(self, structure: Dict[str, List[str]]) -> str:
        """
        Generate natural language profile text from structured data.
        
        This creates a format similar to create_user_profile_document output.
        """
        sections = []
        
        # Skin Profile section
        skin_parts = []
        if structure.get("skin_type"):
            skin_parts.extend(structure["skin_type"])
        if structure.get("skin_concerns"):
            for concern in structure["skin_concerns"]:
                skin_parts.append(f"treating {concern}")
        
        if skin_parts:
            sections.append(f"[Skin Profile]. {'. '.join(skin_parts)}.")
        
        # Hair Profile section
        if structure.get("hair_goals"):
            hair_goals = [f"wants to {goal}" for goal in structure["hair_goals"]]
            sections.append(f"[Hair Profile]. {'. '.join(hair_goals)}.")
        
        # Preferences section
        pref_parts = []
        if structure.get("preferences"):
            for pref in structure["preferences"]:
                pref_parts.append(f"prefers {pref}")
        if structure.get("allergies"):
            for allergy in structure["allergies"]:
                pref_parts.append(f"allergic to {allergy}")
        
        if pref_parts:
            sections.append(f"[Preferences]. {'. '.join(pref_parts)}.")
        
        return " ".join(sections)
    
    def get_profile_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the user's profile.
        
        Returns:
            Dictionary with profile statistics
        """
        try:
            profile = self.get_current_profile()
            if not profile["success"]:
                return profile
            
            profile_text = profile.get("profile_text", "")
            
            # Count sections
            sections = ["[Skin Profile]", "[Hair Profile]", "[Preferences]"]
            section_counts = {}
            for section in sections:
                section_counts[section.replace("[", "").replace("]", "").lower()] = (
                    1 if section in profile_text else 0
                )
            
            return {
                "success": True,
                "user_id": self.authenticated_user_id,
                "character_count": len(profile_text),
                "word_count": len(profile_text.split()) if profile_text else 0,
                "sections_present": section_counts,
                "has_embedding": profile.get("has_embedding", False),
                "last_updated": profile.get("updated_at")
            }
        
        except Exception as e:
            self.logger.error(f"Error getting profile statistics: {e}")
            return {
                "success": False,
                "error": f"Statistics error: {str(e)}"
            }


def user_profile_tool(user_id: int, update_type: str, column: str, new_value: Union[str, int, List[str]]) -> str:
    """
    Main UserProfileTool function matching the exact specification:
    - Input: user_id, update_type(update, add, remove), column name, information to update  
    - Execute single, safe update query
    - Only for authenticated user and users table only
    
    Args:
        user_id: ID of the authenticated user
        update_type: 'update', 'add', or 'remove' 
        column: column/section to modify (embedding_text or profile sections)
        new_value: information to update
        
    Returns:
        String message with operation result
    """
    try:
        tool = UserProfileTool(user_id)
        
        if update_type == "update":
            if column == "embedding_text":
                result = tool.update_profile_text(str(new_value))
            else:
                # Treat as section update
                values = [str(new_value)] if not isinstance(new_value, list) else [str(v) for v in new_value]
                result = tool.update_profile_section(column, values)
        
        elif update_type == "add":
            values = [str(new_value)] if not isinstance(new_value, list) else [str(v) for v in new_value]
            result = tool.add_to_profile_section(column, values)
        
        elif update_type == "remove":
            values = [str(new_value)] if not isinstance(new_value, list) else [str(v) for v in new_value]
            result = tool.remove_from_profile_section(column, values)
        
        else:
            return f"Error: Invalid update_type '{update_type}'"
        
        if result["success"]:
            return result["message"]
        else:
            return f"Error: {result['error']}"
    
    except Exception as e:
        return f"Error: {str(e)}"


# Example usage and testing
def example_usage():
    """Example of how to use the improved UserProfileTool"""
    
    try:
        # Initialize tool for user
        user_id = 1
        tool = UserProfileTool(authenticated_user_id=user_id)
        
        print("=== User Profile Tool Example ===")
        
        # Get current profile
        current = tool.get_current_profile()
        print(f"Current profile: {current}")
        
        # Update complete profile text
        new_profile = "[Skin Profile]. Oily skin type, treating acne and blackheads. [Hair Profile]. Wants to add volume and improve shine. [Preferences]. Prefers natural products, allergic to parabens."
        
        result = tool.update_profile_text(new_profile)
        print(f"Profile update result: {result}")
        
        # Add to a specific section
        result = tool.add_to_profile_section("skin_concerns", ["rosacea"])
        print(f"Add to section result: {result}")
        
        # Remove from a section
        result = tool.remove_from_profile_section("skin_concerns", ["blackheads"])
        print(f"Remove from section result: {result}")
        
        # Get statistics
        stats = tool.get_profile_statistics()
        print(f"Profile statistics: {stats}")
        
        # Test backwards compatibility
        compat_result = user_profile_tool(user_id, "update", "preferences", "organic products")
        print(f"Backwards compatible result: {compat_result}")
        
    except Exception as e:
        print(f"Example error: {e}")


if __name__ == "__main__":
    example_usage()