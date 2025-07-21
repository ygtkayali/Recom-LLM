#!/usr/bin/env python
"""
Database utility functions for SmartBeauty application.

This module provides utility functions for common database operations,
table management, and data validation.
"""

import sys
import os
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime

# Add parent directory to path for imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from db.connection import get_database_manager, get_table_info


def check_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        True if table exists, False otherwise
    """
    try:
        table_info = get_table_info(table_name)
        return table_info.get('exists', False)
    except Exception as e:
        print(f"❌ Error checking table existence: {e}")
        return False


def get_table_row_count(table_name: str) -> int:
    """
    Get the number of rows in a table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Number of rows, -1 if error
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                return cursor.fetchone()[0]
    except Exception as e:
        print(f"❌ Error getting row count for {table_name}: {e}")
        return -1


def get_tables_with_embeddings_status() -> Dict[str, Dict[str, int]]:
    """
    Get status of embedding vectors in all tables.
    
    Returns:
        Dictionary with table names and their embedding status
    """
    embedding_tables = ['products', 'concepts']
    status = {}
    
    for table_name in embedding_tables:
        if not check_table_exists(table_name):
            status[table_name] = {'exists': False}
            continue
            
        try:
            with get_database_manager().get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Total rows
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total = cursor.fetchone()[0]
                    
                    # Rows with embeddings
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
                    with_embeddings = cursor.fetchone()[0]
                    
                    status[table_name] = {
                        'exists': True,
                        'total_rows': total,
                        'with_embeddings': with_embeddings,
                        'without_embeddings': total - with_embeddings,
                        'completion_percentage': (with_embeddings / total * 100) if total > 0 else 0
                    }
                    
        except Exception as e:
            print(f"❌ Error getting embedding status for {table_name}: {e}")
            status[table_name] = {'exists': True, 'error': str(e)}
    
    return status


def truncate_table(table_name: str) -> bool:
    """
    Truncate a table (remove all rows).
    
    Args:
        table_name: Name of the table to truncate
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                conn.commit()
                print(f"✅ Table {table_name} truncated successfully")
                return True
    except Exception as e:
        print(f"❌ Error truncating table {table_name}: {e}")
        return False


def backup_table_data(table_name: str, output_file: Optional[str] = None) -> bool:
    """
    Backup table data to JSON file.
    
    Args:
        table_name: Name of the table to backup
        output_file: Output file path (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{table_name}_backup_{timestamp}.json"
    
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in cursor.fetchall()]
                
                # Convert rows to dictionaries
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        # Handle special data types
                        if isinstance(value, datetime):
                            row_dict[columns[i]] = value.isoformat()
                        elif hasattr(value, 'tolist'):  # For numpy arrays/vectors
                            row_dict[columns[i]] = value.tolist()
                        else:
                            row_dict[columns[i]] = value
                    data.append(row_dict)
                
                # Write to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'table_name': table_name,
                        'backup_timestamp': datetime.now().isoformat(),
                        'row_count': len(data),
                        'columns': columns,
                        'data': data
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Table {table_name} backed up to {output_file} ({len(data)} rows)")
                return True
                
    except Exception as e:
        print(f"❌ Error backing up table {table_name}: {e}")
        return False


def get_database_schema_summary() -> Dict[str, Any]:
    """
    Get a summary of the database schema.
    
    Returns:
        Dictionary with schema information
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get all tables
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                schema_info = {
                    'database_name': conn.get_dsn_parameters()['dbname'],
                    'tables': {},
                    'total_tables': len(tables)
                }
                
                for table_name in tables:
                    table_info = get_table_info(table_name)
                    schema_info['tables'][table_name] = table_info
                
                return schema_info
                
    except Exception as e:
        print(f"❌ Error getting database schema: {e}")
        return {'error': str(e)}


def optimize_database() -> bool:
    """
    Optimize database by running VACUUM and ANALYZE.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            # Set autocommit for VACUUM
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                print("🔧 Running VACUUM...")
                cursor.execute("VACUUM")
                
                print("🔧 Running ANALYZE...")
                cursor.execute("ANALYZE")
                
                print("✅ Database optimization completed")
                return True
                
    except Exception as e:
        print(f"❌ Error optimizing database: {e}")
        return False
    finally:
        # Reset autocommit
        if 'conn' in locals():
            conn.autocommit = False


def check_indexes_status(table_name: str) -> Dict[str, Any]:
    """
    Check the status of indexes for a table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dictionary with index information
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT indexname, indexdef 
                    FROM pg_indexes 
                    WHERE tablename = %s
                    ORDER BY indexname
                """, (table_name,))
                
                indexes = cursor.fetchall()
                
                return {
                    'table_name': table_name,
                    'index_count': len(indexes),
                    'indexes': [
                        {'name': idx[0], 'definition': idx[1]} 
                        for idx in indexes
                    ]
                }
                
    except Exception as e:
        print(f"❌ Error checking indexes for {table_name}: {e}")
        return {'error': str(e)}


def validate_vector_dimensions(table_name: str, expected_dim: int = 384) -> Dict[str, Any]:
    """
    Validate vector dimensions in embedding columns.
    
    Args:
        table_name: Name of the table
        expected_dim: Expected vector dimension
        
    Returns:
        Dictionary with validation results
    """
    try:
        with get_database_manager().get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if embedding column exists
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = 'embedding'
                """)
                
                embedding_column = cursor.fetchone()
                if not embedding_column:
                    return {'error': 'No embedding column found'}
                
                # Check vector dimensions
                cursor.execute(f"""
                    SELECT id, array_length(embedding, 1) as dim_size
                    FROM {table_name} 
                    WHERE embedding IS NOT NULL
                    LIMIT 10
                """)
                
                samples = cursor.fetchall()
                
                # Analyze dimensions
                dimension_counts = {}
                for sample_id, dim_size in samples:
                    if dim_size not in dimension_counts:
                        dimension_counts[dim_size] = 0
                    dimension_counts[dim_size] += 1
                
                return {
                    'table_name': table_name,
                    'embedding_column_exists': True,
                    'expected_dimension': expected_dim,
                    'dimension_distribution': dimension_counts,
                    'samples_checked': len(samples),
                    'all_correct_dimension': all(dim == expected_dim for _, dim in samples) if samples else None
                }
                
    except Exception as e:
        print(f"❌ Error validating vector dimensions for {table_name}: {e}")
        return {'error': str(e)}