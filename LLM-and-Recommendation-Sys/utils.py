import os
import sys
import json
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2 import Error

def load_environment() -> Dict[str, Any]:
    """
    Load environment variable"s from .env file if it exists
    """
    load_dotenv()
    
    env_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DATABASE_URL': os.getenv('DATABASE_URL')
    }
    
    return env_vars

def check_requirements() -> Dict[str, bool]:
    """
    Check if all required dependencies are installed
    """
    requirements = {
        'langchain': True,
        'openai': True,
        'pgvector': True,
        'psycopg2': True,
        'sentence_transformers': True
    }
    
    try:
        import langchain
    except ImportError:
        requirements['langchain'] = False
        
    try:
        import openai
    except ImportError:
        requirements['openai'] = False
        
    try:
        import pgvector
    except ImportError:
        requirements['pgvector'] = False
        
    try:
        import psycopg2
    except ImportError:
        requirements['psycopg2'] = False
        
    try:
        import sentence_transformers
    except ImportError:
        requirements['sentence_transformers'] = False
        
    return requirements

def setup_environment() -> bool:
    """
    Setup and validate the environment for the RAG system.
    
    Returns:
        True if environment is properly set up, False otherwise
    """
    print("🔧 Setting up environment...")
    
    # Load environment variables
    env_vars = load_environment()
    
    # Check required environment variables
    missing_vars = []
    if not env_vars['OPENAI_API_KEY']:
        missing_vars.append('OPENAI_API_KEY')
    if not env_vars['DATABASE_URL']:
        missing_vars.append('DATABASE_URL')
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    
    # Check requirements
    requirements = check_requirements()
    missing_reqs = [req for req, installed in requirements.items() if not installed]
    
    if missing_reqs:
        print(f"❌ Missing dependencies: {', '.join(missing_reqs)}")
        print("Please install missing packages")
        return False
    
    print("✅ Environment setup successful")
    return True

def parse_connection_string(connection_string: str) -> Tuple[str, str, str, str, str]:
    """
    Parse a SQLAlchemy connection string into individual components.
    
    Args:
        connection_string: SQLAlchemy connection string format
                          Example: postgresql+psycopg2://postgres:password@localhost:5433/smartbeauty
    
    Returns:
        Tuple of (host, port, user, password, dbname)
    """
    try:
        # Extract the part after postgresql+psycopg2://
        params_part = connection_string.split("://")[1]
        
        # Split user:password@host:port/dbname
        user_pass, host_port_db = params_part.split("@")
        user, password = user_pass.split(":")
        
        # Handle host:port/dbname
        if "/" in host_port_db:
            host_port, dbname = host_port_db.split("/")
        else:
            host_port, dbname = host_port_db, ""
            
        # Handle host:port
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, "5432"
            
        return host, port, user, password, dbname
    except Exception as e:
        raise ValueError(f"Failed to parse connection string: {e}")

def test_db_connection(connection_string: str, table_name: str = None) -> bool:
    """
    Test database connection and optionally check if a table exists.
    
    Args:
        connection_string: Database connection string
        table_name: Optional table name to check for existence
        
    Returns:
        True if connection successful (and table exists if specified), False otherwise
    """
    try:
        host, port, user, password, dbname = parse_connection_string(connection_string)
        
        print(f"Connecting to {host}:{port} as {user} to database {dbname}")
        
        # Create a direct connection using psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        
        print("Successfully connected to the PostgreSQL database!")
        
        cursor = conn.cursor()
        
        # Check if table exists (if table_name is provided)
        if table_name:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table_name,))
            
            table_exists = cursor.fetchone()[0]
            if table_exists:
                print(f"The table '{table_name}' exists!")
                
                # Count rows
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"Table '{table_name}' has {count} rows.")
            else:
                print(f"The table '{table_name}' does not exist.")
                cursor.close()
                conn.close()
                return False
                
        # Close cursor and connection
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def get_db_connection_params() -> Dict[str, str]:
    """
    Get database connection parameters from config.
    
    Returns:
        Dictionary with database connection parameters
    """
    from rag.core import config
    
    return {
        "host": config.DATABASE_HOST,
        "port": config.DATABASE_PORT,
        "user": config.DATABASE_USER,
        "password": config.DATABASE_PASSWORD,
        "dbname": config.DATABASE_NAME
    }

def create_db_connection_from_config() -> Optional[psycopg2.extensions.connection]:
    """
    Create a PostgreSQL database connection using individual config parameters.
    
    Returns:
        psycopg2 connection object or None if connection fails
    """
    try:
        params = get_db_connection_params()
        
        print(f"Connecting to {params['host']}:{params['port']} as {params['user']} to database {params['dbname']}")
        
        # Create a direct connection using psycopg2
        conn = psycopg2.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            dbname=params['dbname']
        )
        
        print("Successfully connected to the PostgreSQL database!")
        return conn
        
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_related_skin_conditions_for_product(product_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Get skin conditions related to a product by comparing embedding similarities.
    
    Args:
        product_id: The ID of the product to find related skin conditions for
        top_n: Number of top related skin conditions to return (default: 5)
        
    Returns:
        List of dictionaries containing skin condition info and similarity scores
    """
    import json
    
    conn = create_db_connection_from_config()
    if not conn:
        print("Failed to connect to database")
        return []
        
    try:
        cursor = conn.cursor()
        
        # First, get the product embedding from langchain_pg_embedding table
        cursor.execute("""
        SELECT embedding, document, cmetadata
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'products'
        )
        AND cmetadata->>'product_id' = %s
        """, (product_id,))
        product_result = cursor.fetchone()
        if not product_result:
            print(f"Product with ID {product_id} not found in embeddings")
            return []
            
        product_embedding = product_result[0]
        product_document = product_result[1]
        product_metadata = product_result[2]  # Already a dict
        
        print(f"Found product: {product_metadata.get('name', 'Unknown')}")
        
        # Get all skin condition embeddings and calculate similarities
        cursor.execute("""
        SELECT 
            embedding,
            document,
            cmetadata,
            1 - (embedding <=> %s::vector) AS similarity
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'skin_conditions'
        )
        ORDER BY similarity DESC
        LIMIT %s        """, (str(product_embedding), top_n))
        
        skin_condition_results = cursor.fetchall()
        
        related_conditions = []
        for result in skin_condition_results:
            embedding, document, metadata, similarity = result
            # metadata is already a dict, no need to parse JSON
            
            related_conditions.append({
                "condition_id": metadata.get("condition_id"),
                "condition_name": metadata.get("condition_name"),
                "document": document,
                "similarity": float(similarity),
                "metadata": metadata
            })
        
        cursor.close()
        conn.close()
        
        return related_conditions
        
    except Exception as e:
        print(f"Error finding related skin conditions: {e}")
        if conn:
            conn.close()
        return []

def get_related_products_for_skin_condition(condition_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Get products related to a skin condition by comparing embedding similarities.
    
    Args:
        condition_id: The ID of the skin condition to find related products for
        top_n: Number of top related products to return (default: 5)
        
    Returns:
        List of dictionaries containing product info and similarity scores
    """
    import json
    
    conn = create_db_connection_from_config()
    if not conn:
        print("Failed to connect to database")
        return []
        
    try:
        cursor = conn.cursor()
        
        # First, get the skin condition embedding
        cursor.execute("""
        SELECT embedding, document, cmetadata
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'skin_conditions'
        )
        AND cmetadata->>'condition_id' = %s
        """, (condition_id,))
        
        condition_result = cursor.fetchone()
        if not condition_result:
            print(f"Skin condition with ID {condition_id} not found in embeddings")
            return []
            
        condition_embedding = condition_result[0]
        condition_document = condition_result[1]
        condition_metadata = condition_result[2]  # Already a dict
        
        print(f"Found skin condition: {condition_metadata.get('condition_name', 'Unknown')}")
        
        # Get all product embeddings and calculate similarities
        cursor.execute("""
        SELECT 
            embedding,
            document,
            cmetadata,
            1 - (embedding <=> %s::vector) AS similarity
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'products'
        )
        ORDER BY similarity DESC
        LIMIT %s
        """, (str(condition_embedding), top_n))
        
        product_results = cursor.fetchall()
        
        related_products = []
        for result in product_results:
            embedding, document, metadata, similarity = result
            # metadata is already a dict, no need to parse JSON
            
            related_products.append({
                "product_id": metadata.get("product_id"),
                "product_name": metadata.get("name"),
                "document": document,
                "similarity": float(similarity),
                "metadata": metadata
            })
        
        cursor.close()
        conn.close()
        
        return related_products
        
    except Exception as e:
        print(f"Error finding related products: {e}")
        if conn:
            conn.close()
        return []

def create_query_embedding(query: str, embedding_model=None) -> Optional[List[float]]:
    """
    Create embedding for user query using the same model used for skin conditions and products.
    
    Args:
        query: User query text
        embedding_model: Optional embedding model instance. If None, creates a new one.
        
    Returns:
        Embedding vector as list of floats or None if failed
    """
    try:
        # Import here to avoid circular imports
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from .rag.core import config
        
        if embedding_model is None:
            embedding_model = HuggingFaceEmbeddings(
                model_name=config.SENTENCE_TRANSFORMER_MODEL_NAME,
                model_kwargs={'device': 'cpu'}
            )
        
        # Generate embedding for the query
        query_embedding = embedding_model.embed_query(query)
        print(f"✓ Created embedding for query: '{query[:50]}...'")
        return query_embedding
        
    except Exception as e:
        print(f"❌ Error creating query embedding: {e}")
        return None

def find_matching_skin_condition_by_query(query: str, top_n: int = 3, similarity_threshold: float = 0.6) -> List[Dict[str, Any]]:
    """
    Step 1-3 of RAG Pipeline: Find skin condition that best matches the user query.
    
    Args:
        query: User query (e.g., "I have acne problems" or "oily skin")
        top_n: Number of top matching skin conditions to return
        similarity_threshold: Minimum similarity score to include
        
    Returns:
        List of matching skin conditions with similarity scores
    """
    print(f"🔍 Step 1-3: Finding skin conditions matching query: '{query}'")
    
    # Step 2: Create embedding for query
    query_embedding = create_query_embedding(query)
    if not query_embedding:
        return []
    
    # Step 3: Find matching skin conditions
    conn = create_db_connection_from_config()
    if not conn:
        print("Failed to connect to database")
        return []
    
    try:
        cursor = conn.cursor()
        
        # Convert query embedding to vector format for database
        query_embedding_str = str(query_embedding)
        
        # Find skin conditions similar to the query
        cursor.execute("""
        SELECT 
            cmetadata,
            document,
            1 - (embedding <=> %s::vector) AS similarity
        FROM langchain_pg_embedding 
        WHERE collection_id = (
            SELECT uuid FROM langchain_pg_collection WHERE name = 'skin_conditions'
        )
        ORDER BY similarity DESC
        LIMIT %s
        """, (query_embedding_str, top_n))
        
        results = []
        for row in cursor.fetchall():
            metadata, document, similarity = row
            
            if float(similarity) >= similarity_threshold:
                results.append({
                    "condition_id": metadata.get("condition_id"),
                    "condition_name": metadata.get("condition_name"),
                    "document": document,
                    "similarity": float(similarity),
                    "metadata": metadata
                })
        
        cursor.close()
        conn.close()
        
        print(f"✓ Found {len(results)} matching skin conditions")
        for result in results:
            print(f"  - {result['condition_name']} (similarity: {result['similarity']:.3f})")
        return results
        
    except Exception as e:
        print(f"❌ Error finding matching skin conditions: {e}")
        if conn:
            conn.close()
        return []

def get_embedding_collection_info() -> Dict[str, Any]:
    """
    Get information about the embedding collections in the database.
    
    Returns:
        Dictionary with collection information
    """
    conn = create_db_connection_from_config()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        # Get collection information
        cursor.execute("""
            SELECT 
                c.name as collection_name,
                COUNT(e.uuid) as embedding_count,
                MAX(e.cmetadata::json->>'document_type') as doc_type
            FROM langchain_pg_collection c
            LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id
            GROUP BY c.name, c.uuid
            ORDER BY c.name;
        """)
        
        collections = {}
        for row in cursor.fetchall():
            name, count, doc_type = row
            collections[name] = {
                'count': count or 0,
                'document_type': doc_type
            }
        
        cursor.close()
        conn.close()
        
        return collections
        
    except Exception as e:
        print(f"Error getting collection info: {e}")
        if conn:
            conn.close()
        return {}

def validate_database_schema() -> bool:
    """
    Validate that the database has the required tables and structure.
    
    Returns:
        True if schema is valid, False otherwise
    """
    conn = create_db_connection_from_config()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = ['langchain_pg_collection', 'langchain_pg_embedding', 'products', 'skin_conditions']
        
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            exists = cursor.fetchone()[0]
            if not exists:
                print(f"❌ Required table '{table}' not found")
                cursor.close()
                conn.close()
                return False
        
        # Check if embeddings exist
        cursor.execute("""
            SELECT COUNT(*) FROM langchain_pg_embedding;
        """)
        embedding_count = cursor.fetchone()[0]
        
        if embedding_count == 0:
            print("❌ No embeddings found in database")
            cursor.close()
            conn.close()
            return False
        
        cursor.close()
        conn.close()
        print(f"✅ Database schema valid ({embedding_count} embeddings found)")
        return True
        
    except Exception as e:
        print(f"❌ Error validating database schema: {e}")
        if conn:
            conn.close()
        return False

def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status information.
    
    Returns:
        Dictionary with system status
    """
    status = {
        'environment': setup_environment(),
        'database_connection': test_db_connection(os.getenv('DATABASE_URL', '')),
        'database_schema': validate_database_schema(),
        'collections': get_embedding_collection_info(),
        'timestamp': datetime.now().isoformat()
    }
    
    return status

def debug_embedding_search(query: str, collection_name: str = 'products', top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Debug function to test embedding search with detailed output.
    
    Args:
        query: Query to search for
        collection_name: Collection to search in ('products' or 'skin_conditions')
        top_k: Number of results to return
        
    Returns:
        List of search results with detailed information
    """
    print(f"🔍 Debug search: '{query}' in '{collection_name}' collection")
    
    # Create query embedding
    query_embedding = create_query_embedding(query)
    if not query_embedding:
        return []
    
    conn = create_db_connection_from_config()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Search for similar embeddings
        cursor.execute("""
            SELECT 
                cmetadata,
                document,
                1 - (embedding <=> %s::vector) AS similarity
            FROM langchain_pg_embedding 
            WHERE collection_id = (
                SELECT uuid FROM langchain_pg_collection WHERE name = %s
            )
            ORDER BY similarity DESC
            LIMIT %s
        """, (str(query_embedding), collection_name, top_k))
        
        results = []
        for i, row in enumerate(cursor.fetchall(), 1):
            metadata, document, similarity = row
            
            result = {
                'rank': i,
                'similarity': float(similarity),
                'metadata': metadata,
                'document_preview': document[:200] + '...' if len(document) > 200 else document,
                'full_document': document
            }
            
            # Add type-specific fields
            if collection_name == 'products':
                result['name'] = metadata.get('name', 'Unknown')
                result['product_id'] = metadata.get('product_id', 'Unknown')
            elif collection_name == 'skin_conditions':
                result['name'] = metadata.get('condition_name', 'Unknown')
                result['condition_id'] = metadata.get('condition_id', 'Unknown')
            
            results.append(result)
            
            print(f"  {i}. {result['name']} (similarity: {similarity:.4f})")
        
        cursor.close()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Error in debug search: {e}")
        if conn:
            conn.close()
        return []

def cleanup_database_connections():
    """
    Cleanup any lingering database connections.
    """
    try:
        # Force garbage collection to clean up connections
        import gc
        gc.collect()
        print("✅ Database connections cleaned up")
    except Exception as e:
        print(f"Error cleaning up connections: {e}")

def get_database_stats() -> Dict[str, Any]:
    """
    Get detailed database statistics.
    
    Returns:
        Dictionary with database statistics
    """
    conn = create_db_connection_from_config()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        
        stats = {}
        
        # Basic table counts
        tables = ['products', 'skin_conditions', 'langchain_pg_embedding', 'langchain_pg_collection']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                stats[f'{table}_count'] = cursor.fetchone()[0]
            except:
                stats[f'{table}_count'] = 0
        
        # Embedding collection stats
        cursor.execute("""
            SELECT 
                c.name,
                COUNT(e.uuid) as count,
                AVG(array_length(string_to_array(e.embedding::text, ','), 1)) as avg_dim
            FROM langchain_pg_collection c
            LEFT JOIN langchain_pg_embedding e ON c.uuid = e.collection_id
            GROUP BY c.name;
        """)
        
        collections = {}
        for row in cursor.fetchall():
            name, count, avg_dim = row
            collections[name] = {
                'count': count or 0,
                'avg_dimensions': int(avg_dim) if avg_dim else 0
            }
        
        stats['collections'] = collections
        
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        print(f"Error getting database stats: {e}")
        if conn:
            conn.close()
        return {}

