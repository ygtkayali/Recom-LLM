#!/usr/bin/env python
"""
Script to test the database connection using the new connection system.

This script:
1. Tests the basic database connection
2. Checks for required extensions (pgvector)
3. Validates environment variables
4. Shows database information

Usage:
python test_connection.py [--verbose] [--check-tables]
"""
import os
import sys
import argparse
from datetime import datetime

# Add the parent directory to sys.path to import local modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from db.connection import (
    get_database_manager, test_db_connection, DatabaseConfig
)
from db.utils import get_database_schema_summary, check_table_exists


def test_environment_variables():
    """Test and display environment variables."""
    print("🔧 Environment Variables Check:")
    print("-" * 30)
    
    required_vars = [
        'DATABASE_HOST',
        'DATABASE_PORT', 
        'DATABASE_NAME',
        'DATABASE_USER',
        'DATABASE_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask password
            display_value = '***' if 'PASSWORD' in var else value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    
    return True


def test_database_info():
    """Test database connection and get basic information."""
    print("\n💾 Database Information:")
    print("-" * 30)
    
    try:
        config = DatabaseConfig()
        print(f"  Host: {config.host}")
        print(f"  Port: {config.port}")
        print(f"  Database: {config.database}")
        print(f"  User: {config.user}")
        print(f"  Connection String: {config.get_connection_string().replace(config.password, '***')}")
        
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get PostgreSQL version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                print(f"  PostgreSQL Version: {version.split(',')[0]}")
                
                # Get database size
                cursor.execute(f"""
                    SELECT pg_size_pretty(pg_database_size('{config.database}'))
                """)
                db_size = cursor.fetchone()[0]
                print(f"  Database Size: {db_size}")
                
                # Check extensions
                cursor.execute("""
                    SELECT extname, extversion 
                    FROM pg_extension 
                    WHERE extname IN ('vector', 'uuid-ossp', 'hstore')
                    ORDER BY extname
                """)
                extensions = cursor.fetchall()
                print(f"  Extensions:")
                if extensions:
                    for ext_name, ext_version in extensions:
                        print(f"    - {ext_name}: v{ext_version}")
                else:
                    print("    - No relevant extensions found")
                
                return True
                
    except Exception as e:
        print(f"  ❌ Error getting database info: {e}")
        return False


def test_table_status():
    """Test table existence and basic status."""
    print("\n📊 Table Status:")
    print("-" * 30)
    
    expected_tables = ['products', 'concepts']
    
    for table_name in expected_tables:
        exists = check_table_exists(table_name)
        if exists:
            try:
                with get_database_manager().get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        # Get row count
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        
                        # Check for embedding column
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM information_schema.columns 
                            WHERE table_name = '{table_name}' AND column_name = 'embedding'
                        """)
                        has_embedding_col = cursor.fetchone()[0] > 0
                        
                        embedding_status = ""
                        if has_embedding_col:
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
                            with_embeddings = cursor.fetchone()[0]
                            embedding_status = f" ({with_embeddings} with embeddings)"
                        
                        print(f"  ✅ {table_name}: {row_count} rows{embedding_status}")
                        
            except Exception as e:
                print(f"  ⚠️ {table_name}: exists but error getting details - {e}")
        else:
            print(f"  ❌ {table_name}: does not exist")


def test_connection_pool():
    """Test database connection pooling."""
    print("\n🏊‍♀️ Connection Pool Test:")
    print("-" * 30)
    
    try:
        db_manager = get_database_manager()
        
        # Test multiple connections
        connections = []
        for i in range(3):
            conn = db_manager.get_connection()
            connections.append(conn)
            print(f"  ✅ Connection {i+1}: acquired")
        
        # Return connections
        for i, conn in enumerate(connections):
            db_manager.return_connection(conn)
            print(f"  ✅ Connection {i+1}: returned")
        
        print("  ✅ Connection pool test successful")
        return True
        
    except Exception as e:
        print(f"  ❌ Connection pool test failed: {e}")
        return False


def run_performance_test():
    """Run a simple performance test."""
    print("\n⚡ Performance Test:")
    print("-" * 30)
    
    try:
        start_time = datetime.now()
        
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Run a simple query multiple times
                for i in range(10):
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"  ✅ 10 simple queries completed in {duration:.3f} seconds")
        print(f"  ✅ Average query time: {duration/10*1000:.2f} ms")
        return True
        
    except Exception as e:
        print(f"  ❌ Performance test failed: {e}")
        return False


def main():
    """Main function to test database connection."""
    parser = argparse.ArgumentParser(description='Test SmartBeauty database connection')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed information')
    parser.add_argument('--check-tables', action='store_true',
                       help='Check table status')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance test')
    parser.add_argument('--schema', action='store_true',
                       help='Show database schema summary')
    
    args = parser.parse_args()
    
    print("🔍 SmartBeauty Database Connection Test")
    print("=" * 50)
    
    # Test environment variables
    if not test_environment_variables():
        return False
    
    # Test basic connection
    print("\n🔌 Basic Connection Test:")
    print("-" * 30)
    if test_db_connection():
        print("  ✅ Basic connection test passed")
    else:
        print("  ❌ Basic connection test failed")
        return False
    
    # Test database info
    if not test_database_info():
        return False
    
    # Test connection pool
    if not test_connection_pool():
        return False
    
    # Test table status
    if args.check_tables:
        test_table_status()
    
    # Run performance test
    if args.performance:
        run_performance_test()
    
    # Show schema summary
    if args.schema:
        print("\n📋 Database Schema Summary:")
        print("-" * 30)
        schema = get_database_schema_summary()
        if 'error' not in schema:
            print(f"  Database: {schema['database_name']}")
            print(f"  Total tables: {schema['total_tables']}")
            for table_name, table_info in schema['tables'].items():
                if table_info.get('exists', False):
                    print(f"    - {table_name}: {table_info['row_count']} rows, {len(table_info['columns'])} columns")
        else:
            print(f"  ❌ Error getting schema: {schema['error']}")
    
    print("\n🎉 Database connection test completed successfully!")
    print("\n💡 Next steps:")
    print("  - Run: python table_creation.py --create-indexes")
    print("  - Run: python populate_products_table.py --dry-run") 
    print("  - Run: python populate_concepts_table.py --dry-run")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
