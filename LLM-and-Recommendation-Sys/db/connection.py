#!/usr/bin/env python
"""
Database connection module for SmartBeauty application.

This module provides centralized database connection management using environment variables
and includes connection pooling, error handling, and database utilities.
"""

import os
import sys
from typing import Dict, Any, Optional, Tuple
from contextlib import contextmanager
import psycopg2
from psycopg2 import Error, pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseConfig:
    """Database configuration class using environment variables."""
    
    def __init__(self):
        """Initialize database configuration from environment variables."""
        self.host = os.getenv('DATABASE_HOST', 'localhost')
        self.port = os.getenv('DATABASE_PORT', '5432')
        self.database = os.getenv('DATABASE_NAME', 'smartbeauty')
        self.user = os.getenv('DATABASE_USER', 'postgres')
        self.password = os.getenv('DATABASE_PASSWORD', '')
        
        # Validate required parameters
        if not self.password:
            raise ValueError("DATABASE_PASSWORD environment variable is required")
    
    def get_connection_params(self) -> Dict[str, str]:
        """Get database connection parameters as dictionary."""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }
    
    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseManager:
    """Database connection manager with connection pooling."""
    
    def __init__(self, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize database manager with connection pooling.
        
        Args:
            min_conn: Minimum number of connections in pool
            max_conn: Maximum number of connections in pool
        """
        self.config = DatabaseConfig()
        self.connection_pool = None
        self.min_conn = min_conn
        self.max_conn = max_conn
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_conn,
                self.max_conn,
                **self.config.get_connection_params()
            )
            print(f"✅ Database connection pool initialized ({self.min_conn}-{self.max_conn} connections)")
        except Exception as e:
            print(f"❌ Failed to initialize connection pool: {e}")
            raise
    
    def get_connection(self) -> psycopg2.extensions.connection:
        """
        Get a connection from the pool.
        
        Returns:
            Database connection from pool
        """
        if not self.connection_pool:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            conn = self.connection_pool.getconn()
            if conn.closed:
                # Connection is closed, get a new one
                self.connection_pool.putconn(conn, close=True)
                conn = self.connection_pool.getconn()
            return conn
        except Exception as e:
            print(f"❌ Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn: psycopg2.extensions.connection, close: bool = False):
        """
        Return a connection to the pool.
        
        Args:
            conn: Connection to return
            close: Whether to close the connection
        """
        if self.connection_pool and conn:
            try:
                self.connection_pool.putconn(conn, close=close)
            except Exception as e:
                print(f"⚠️ Failed to return connection to pool: {e}")
    
    @contextmanager
    def get_db_connection(self):
        """
        Context manager for database connections.
        
        Usage:
            with db_manager.get_db_connection() as conn:
                # Use connection
                pass
        """
        conn = None
        try:
            conn = self.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                print("✅ All database connections closed")
            except Exception as e:
                print(f"⚠️ Error closing connections: {e}")


# Global database manager instance
db_manager = None

def get_database_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


def create_db_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Create a single database connection (legacy function for compatibility).
    
    Returns:
        Database connection or None if failed
    """
    try:
        config = DatabaseConfig()
        conn = psycopg2.connect(**config.get_connection_params())
        print(f"✅ Connected to database: {config.host}:{config.port}/{config.database}")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def test_db_connection() -> bool:
    """
    Test database connection and basic functionality.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Test basic query
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                print(f"✅ Database connection test successful")
                print(f"PostgreSQL version: {version}")
                
                # Test pgvector extension
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                if cursor.fetchone():
                    print("✅ pgvector extension is available")
                else:
                    print("⚠️ pgvector extension is not installed")
                
                return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


def execute_sql_file(file_path: str, conn: Optional[psycopg2.extensions.connection] = None) -> bool:
    """
    Execute SQL commands from a file.
    
    Args:
        file_path: Path to SQL file
        conn: Optional connection (will create new one if not provided)
        
    Returns:
        True if execution successful, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            print(f"❌ SQL file not found: {file_path}")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        if conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_content)
                conn.commit()
                print(f"✅ Executed SQL file: {file_path}")
                return True
        else:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql_content)
                    conn.commit()
                    print(f"✅ Executed SQL file: {file_path}")
                    return True
                    
    except Exception as e:
        print(f"❌ Failed to execute SQL file {file_path}: {e}")
        return False


def get_table_info(table_name: str) -> Dict[str, Any]:
    """
    Get information about a table structure.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dictionary with table information
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table_name,))
                
                exists = cursor.fetchone()['exists']
                if not exists:
                    return {'exists': False}
                
                # Get column information
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = cursor.fetchone()['count']
                
                return {
                    'exists': True,
                    'columns': [dict(col) for col in columns],
                    'row_count': row_count
                }
                
    except Exception as e:
        print(f"❌ Failed to get table info for {table_name}: {e}")
        return {'exists': False, 'error': str(e)}
