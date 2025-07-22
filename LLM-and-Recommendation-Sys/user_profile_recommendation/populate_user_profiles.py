#!/usr/bin/env python3
"""
User Profile Population Pipeline for SmartBeauty

This pipeline:
1. Fetches user preference data from the API
2. Creates a natural language user profile document
3. Populates the users table in the database
4. Optionally generates embeddings for the user profile

Usage:
# Populate single user with embeddings
python populate_user_profiles.py --user_id 2 --generate_embeddings --verbose

# Batch populate users
python populate_user_profiles.py --batch_populate --start_id 1 --end_id 10 --generate_embeddings

# Generate embeddings for existing users
python populate_user_profiles.py --generate_all_embeddings

# Check statistics
python populate_user_profiles.py --stats
"""

import sys
import os
import argparse
import json
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from create_user_document import create_user_profile_document
from utility.get_preference import get_preference
from db.connection import get_database_manager


class UserProfilePopulator:
    """
    Pipeline class for populating user profiles in the database.
    
    This class handles:
    - Fetching user preferences from API
    - Creating natural language profile documents
    - Inserting user profiles into the users table
    - Optional embedding generation
    """
    
    def __init__(self, generate_embeddings: bool = False):
        """Initialize the user profile populator.
        
        Args:
            generate_embeddings: Whether to generate embeddings immediately after insertion
        """
        self.generate_embeddings = generate_embeddings
    
    def generate_embeddings_for_users(self) -> bool:
        """
        Generate embeddings for users directly without using subprocess.
        
        Returns:
            True if embedding generation was successful
        """
        print("Generating embeddings for users...")
        
        try:
            # Import the required modules directly
            from langchain_community.embeddings import HuggingFaceEmbeddings
            import rag.core.config as config
            
            print(f"Loading embedding model: {config.SENTENCE_TRANSFORMER_MODEL_NAME}...")
            embedding_model = HuggingFaceEmbeddings(
                model_name=config.SENTENCE_TRANSFORMER_MODEL_NAME,
                model_kwargs={'device': 'cpu'}
            )
            print("Embedding model loaded successfully")
            
            # Get users without embeddings
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, embedding_text
                        FROM users
                        WHERE embedding IS NULL AND embedding_text IS NOT NULL
                    """)
                    users_without_embeddings = cursor.fetchall()
            
            if not users_without_embeddings:
                print("No users found without embeddings")
                return True
            
            print(f"Processing {len(users_without_embeddings)} users without embeddings...")
            
            # Process each user
            successful = 0
            for user_id, embedding_text in users_without_embeddings:
                try:
                    print(f"Processing user {user_id}...")
                    
                    # Generate embedding
                    embedding = embedding_model.embed_query(embedding_text)
                    embedding_str = str(embedding)
                    
                    # Update user with embedding
                    with get_database_manager().get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE users
                                SET embedding = %s::vector
                                WHERE id = %s
                            """, (embedding_str, user_id))
                            conn.commit()
                    
                    successful += 1
                    print(f"Updated embedding for user {user_id}")
                    
                except Exception as e:
                    print(f"Error processing user {user_id}: {e}")
            
            print(f"Successfully generated embeddings for {successful}/{len(users_without_embeddings)} users")
            return successful > 0
                
        except Exception as e:
            print(f"Error running embedding generation: {e}")
            return False
    
    def fetch_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch user preferences from the API.
        
        Args:
            user_id: User ID to fetch preferences for
            
        Returns:
            Dictionary with user preferences or None if failed
        """
        print(f"Fetching preferences for user {user_id}...")
        
        try:
            preferences = get_preference(user_id)
            if preferences:
                print(f"Successfully fetched preferences for user {user_id}")
                return preferences
            else:
                print(f"No preferences found for user {user_id}")
                return None
        except Exception as e:
            print(f"Error fetching preferences for user {user_id}: {e}")
            return None
    
    def create_profile_document(self, user_preferences: Dict[str, Any]) -> Optional[str]:
        """
        Create a natural language profile document from user preferences.
        
        Args:
            user_preferences: Dictionary containing user preferences
            
        Returns:
            Profile document string or None if creation failed
        """
        print(f"Creating profile document...")
        
        try:
            if not user_preferences:
                print(f"Empty preferences provided")
                return None
            
            document = create_user_profile_document(user_preferences)
            
            if document and document.strip():
                print(f"Created profile document ({len(document)} characters)")
                return document
            else:
                print(f"Generated empty profile document")
                return None
                
        except Exception as e:
            print(f"Error creating profile document: {e}")
            return None
    
    def insert_user_profile(self, api_user_id: int, profile_document: str) -> Optional[int]:
        """
        Insert or update user profile in the users table using API user ID.
        
        Args:
            api_user_id: API user ID to use as the database ID
            profile_document: Natural language profile document
            
        Returns:
            Database user ID (same as api_user_id) or None if failed
        """
        print("Inserting/updating user profile into database...")
        
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if user already exists
                    cursor.execute("SELECT id FROM users WHERE id = %s", (api_user_id,))
                    existing_user = cursor.fetchone()
                    
                    if existing_user:
                        # Update existing user's profile (reset embedding to NULL so it gets regenerated)
                        cursor.execute("""
                            UPDATE users 
                            SET embedding_text = %s, embedding = NULL
                            WHERE id = %s
                        """, (profile_document, api_user_id))
                        conn.commit()
                        print(f"Updated existing user profile with ID: {api_user_id}")
                        return api_user_id
                    else:
                        # Insert new user profile with specific ID
                        insert_query = """
                            INSERT INTO users (id, embedding_text)
                            VALUES (%s, %s)
                        """
                        
                        cursor.execute(insert_query, (api_user_id, profile_document))
                        conn.commit()
                        
                        print(f"User profile inserted with ID: {api_user_id}")
                        return api_user_id
                    
        except Exception as e:
            print(f"Database error inserting user profile: {e}")
            return None
    
    def check_user_exists(self, user_id: int = None, embedding_text: str = None) -> Optional[int]:
        """
        Check if a user profile already exists in the database.
        
        Args:
            user_id: Database user ID to check
            embedding_text: Embedding text to check for duplicates
            
        Returns:
            Database user ID if exists, None otherwise
        """
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    if user_id:
                        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                    elif embedding_text:
                        cursor.execute("SELECT id FROM users WHERE embedding_text = %s", (embedding_text,))
                    else:
                        return None
                    
                    result = cursor.fetchone()
                    return result[0] if result else None
                    
        except Exception as e:
            print(f"Error checking user existence: {e}")
            return None
    
    def populate_single_user(
        self, 
        api_user_id: int, 
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Complete pipeline for populating a single user profile.
        
        Args:
            api_user_id: User ID from the API
            verbose: Whether to show detailed output
            
        Returns:
            Dictionary with population results
        """
        print(f"\nStarting user profile population for API user {api_user_id}")
        print("=" * 60)
        
        # Step 1: Fetch preferences
        preferences = self.fetch_user_preferences(api_user_id)
        if not preferences:
            return {
                'api_user_id': api_user_id,
                'success': False,
                'error': 'Failed to fetch preferences'
            }
        
        if verbose:
            print(f"Raw preferences:")
            for key, value in preferences.items():
                print(f"   {key}: {value}")
        
        # Step 2: Create profile document
        document = self.create_profile_document(preferences)
        if not document:
            return {
                'api_user_id': api_user_id,
                'success': False,
                'error': 'Failed to create profile document'
            }
        
        if verbose:
            print(f"\nGenerated Profile Document:")
            print("-" * 40)
            print(document)
            print("-" * 40)
        
        # Step 3: Insert/update user profile
        db_user_id = self.insert_user_profile(api_user_id, document)
        if not db_user_id:
            return {
                'api_user_id': api_user_id,
                'success': False,
                'error': 'Failed to insert user profile'
            }
        
        # Step 4: Generate embedding if requested
        embedding_success = True
        if self.generate_embeddings:
            embedding_success = self.generate_embeddings_for_users()
        
        print("Successfully populated user profile!")
        print(f"   API User ID: {api_user_id}")
        print(f"   Database User ID: {db_user_id}")
        print(f"   Document length: {len(document)} characters")
        if self.generate_embeddings:
            print(f"   Embedding generated: {'Yes' if embedding_success else 'Failed'}")
        
        result = {
            'api_user_id': api_user_id,
            'db_user_id': db_user_id,
            'document': document,
            'document_length': len(document),
            'success': True,
            'action': 'created'
        }
        
        if self.generate_embeddings:
            result['embedding_generated'] = embedding_success
        
        return result
    
    def populate_batch_users(
        self,
        start_id: int,
        end_id: int,
        verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Populate multiple user profiles in batch.
        
        Args:
            start_id: Starting user ID (inclusive)
            end_id: Ending user ID (inclusive)
            verbose: Whether to show detailed output
            
        Returns:
            List of population results for each user
        """
        print(f"\nStarting batch user profile population")
        print(f"   User ID range: {start_id} to {end_id}")
        print("=" * 60)
        
        results = []
        successful = 0
        failed = 0
        
        for user_id in range(start_id, end_id + 1):
            result = self.populate_single_user(
                api_user_id=user_id,
                verbose=verbose
            )
            
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
                print(f"Failed to populate user {user_id}: {result.get('error', 'Unknown error')}")
        
        print(f"\nBatch Population Summary:")
        print(f"   Total processed: {len(results)}")
        print(f"   Successfully created/updated: {successful}")
        print(f"   Failed: {failed}")
        
        return results
    
    def get_user_profile_stats(self) -> Dict[str, Any]:
        """
        Get statistics about user profiles in the database.
        
        Returns:
            Dictionary with user profile statistics
        """
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Total users
                    cursor.execute("SELECT COUNT(*) FROM users")
                    total_users = cursor.fetchone()[0]
                    
                    # Users with embeddings
                    cursor.execute("SELECT COUNT(*) FROM users WHERE embedding IS NOT NULL")
                    users_with_embeddings = cursor.fetchone()[0]
                    
                    # Average document length
                    cursor.execute("SELECT AVG(LENGTH(embedding_text)) FROM users WHERE embedding_text IS NOT NULL")
                    avg_doc_length = cursor.fetchone()[0]
                    
                    return {
                        'total_users': total_users,
                        'users_with_embeddings': users_with_embeddings,
                        'users_without_embeddings': total_users - users_with_embeddings,
                        'average_document_length': float(avg_doc_length) if avg_doc_length else 0
                    }
                    
        except Exception as e:
            print(f"Error getting user profile stats: {e}")
            return {}


def display_stats(stats: Dict[str, Any]):
    """Display user profile statistics."""
    if not stats:
        print("No statistics available")
        return
    
    print(f"\nUser Profile Database Statistics:")
    print("=" * 40)
    print(f"Total users: {stats.get('total_users', 0)}")
    print(f"Users with embeddings: {stats.get('users_with_embeddings', 0)}")
    print(f"Users without embeddings: {stats.get('users_without_embeddings', 0)}")
    print(f"Average document length: {stats.get('average_document_length', 0):.1f} characters")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Populate user profiles in database")
    
    # Single user population
    parser.add_argument("--user_id", type=int, help="Single user ID to populate")
    
    # Batch population
    parser.add_argument("--batch_populate", action="store_true", help="Populate users in batch")
    parser.add_argument("--start_id", type=int, default=1, help="Starting user ID for batch")
    parser.add_argument("--end_id", type=int, default=10, help="Ending user ID for batch")
    
    # Options
    parser.add_argument("--generate_embeddings", action="store_true", help="Generate embeddings immediately after insertion")
    parser.add_argument("--generate_all_embeddings", action="store_true", help="Generate embeddings for all existing users without embeddings")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--stats", action="store_true", help="Show user profile statistics")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    
    print("SmartBeauty User Profile Population Pipeline")
    print("=" * 60)
    
    populator = UserProfilePopulator(generate_embeddings=args.generate_embeddings)
    
    # Show stats if requested
    if args.stats:
        stats = populator.get_user_profile_stats()
        display_stats(stats)
        if not (args.user_id or args.batch_populate or args.generate_all_embeddings):
            return
    
    # Generate embeddings for all existing users
    if args.generate_all_embeddings:
        embedding_success = populator.generate_embeddings_for_users()
        if not (args.user_id or args.batch_populate):
            return
    
    results = []
    
    # Single user population
    if args.user_id:
        result = populator.populate_single_user(
            api_user_id=args.user_id,
            verbose=args.verbose
        )
        results = [result]
    
    # Batch population
    elif args.batch_populate:
        results = populator.populate_batch_users(
            start_id=args.start_id,
            end_id=args.end_id,
            verbose=args.verbose
        )
    
    else:
        if not args.generate_all_embeddings:
            print("Please specify either --user_id for single user, --batch_populate for multiple users, or --generate_all_embeddings to generate embeddings for existing users")
            return
    
    # Save results if requested
    if args.output and results:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")
    
    # Show final stats
    if results:
        print(f"\nPipeline completed!")
        final_stats = populator.get_user_profile_stats()
        display_stats(final_stats)


if __name__ == "__main__":
    main()
