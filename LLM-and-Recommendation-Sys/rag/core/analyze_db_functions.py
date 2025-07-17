#!/usr/bin/env python
"""
Script to analyze database connection function usage and identify unused functions.
"""

import os
import re
from typing import Dict, List, Set

def find_function_definitions(file_path: str) -> Set[str]:
    """Find all database connection function definitions in a file."""
    functions = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find function definitions
        pattern = r'def (create_db_connection[^(]*|get_db_connection[^(]*|test_db_connection[^(]*)\('
        matches = re.findall(pattern, content)
        functions.update(matches)
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return functions

def find_function_usages(root_dir: str, function_name: str) -> List[str]:
    """Find all usages of a specific function across the project."""
    usages = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines, 1):
                        # Skip function definitions
                        if f'def {function_name}(' in line:
                            continue
                            
                        # Look for function calls or imports
                        if function_name in line and (
                            f'{function_name}(' in line or
                            f'import {function_name}' in line or
                            f'from' in line and function_name in line
                        ):
                            usages.append(f"{file_path}:{i}")
                            
                except Exception as e:
                    pass  # Skip files that can't be read
    
    return usages

def main():
    """Analyze database connection function usage."""
    print("🔍 Database Connection Function Usage Analysis")
    print("=" * 60)
    
    # Define the utils.py path
    utils_path = r"c:\Projects\Personal Projects\ML\SmartBeauty\LLM\rag\core\utils.py"
    project_root = r"c:\Projects\Personal Projects\ML\SmartBeauty\LLM"
    
    # Find all database connection functions defined in utils.py
    defined_functions = find_function_definitions(utils_path)
    print(f"\n📋 Functions defined in utils.py:")
    for func in sorted(defined_functions):
        print(f"  - {func}")
    
    # Analyze usage for each function
    print(f"\n📊 Usage Analysis:")
    
    unused_functions = []
    used_functions = []
    
    for func in sorted(defined_functions):
        usages = find_function_usages(project_root, func)
        
        # Filter out self-references (usage within utils.py itself)
        external_usages = [u for u in usages if 'utils.py' not in u]
        
        print(f"\n  {func}:")
        print(f"    Total usages: {len(usages)}")
        print(f"    External usages: {len(external_usages)}")
        
        if external_usages:
            used_functions.append(func)
            print(f"    Used in:")
            for usage in external_usages[:5]:  # Show first 5
                file_part = usage.split(':')[0].replace(project_root, '').replace('\\\\', '/')
                print(f"      {file_part}")
            if len(external_usages) > 5:
                print(f"      ... and {len(external_usages) - 5} more")
        else:
            unused_functions.append(func)
            print(f"    ❌ UNUSED (only internal usage)")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"📈 Summary:")
    print(f"  ✅ Used functions ({len(used_functions)}):")
    for func in used_functions:
        print(f"    - {func}")
    
    print(f"  ❌ Unused functions ({len(unused_functions)}):")
    for func in unused_functions:
        print(f"    - {func}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if unused_functions:
        print(f"  - Remove unused functions: {', '.join(unused_functions)}")
    else:
        print(f"  - All functions are being used")
    
    # Check consistency
    print(f"\n🎯 Consistency Check:")
    create_from_config_usages = len(find_function_usages(project_root, 'create_db_connection_from_config'))
    create_usages = len(find_function_usages(project_root, 'create_db_connection'))
    
    print(f"  - create_db_connection_from_config: {create_from_config_usages} usages")
    print(f"  - create_db_connection: {create_usages} usages")
    
    if create_from_config_usages > create_usages:
        print(f"  ✅ System consistently uses create_db_connection_from_config")
    else:
        print(f"  ⚠️  Mixed usage detected")

if __name__ == "__main__":
    main()
