#!/usr/bin/env python3
"""
Script to check for inconsistent import paths that could cause module duplication.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def find_import_inconsistencies(project_root: str):
    """Find files that import the same module using different paths."""
    
    project_path = Path(project_root)
    imports = defaultdict(set)  # module_name -> set of import paths
    
    # Regex patterns for different import styles
    import_patterns = [
        r'from\s+([\w\.]+)\s+import',  # from module import ...
        r'import\s+([\w\.]+)',         # import module
    ]
    
    for py_file in project_path.rglob("*.py"):
        if "/.venv/" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Focus on src.* imports
                    if 'configuration' in match or 'src' in match:
                        module_base = match.split('.')[-1] if '.' in match else match
                        imports[module_base].add((match, str(py_file)))
                        
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    # Find inconsistencies
    inconsistencies = []
    for module, import_paths in imports.items():
        if len(import_paths) > 1:
            # Group by import path
            path_groups = defaultdict(list)
            for import_path, file_path in import_paths:
                path_groups[import_path].append(file_path)
            
            if len(path_groups) > 1:  # Multiple import paths for same module
                inconsistencies.append((module, dict(path_groups)))
    
    return inconsistencies

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inconsistencies = find_import_inconsistencies(project_root)
    
    if inconsistencies:
        print("🚨 Import path inconsistencies found:")
        print("=" * 60)
        
        for module, path_groups in inconsistencies:
            print(f"\nModule: {module}")
            for import_path, files in path_groups.items():
                print(f"  Import path: {import_path}")
                for file_path in files[:3]:  # Show first 3 files
                    print(f"    - {file_path}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more files")
            print()
        
        print("💡 Recommendation: Use consistent absolute imports (src.module.name)")
        return 1
    else:
        print("✅ No import path inconsistencies found!")
        return 0

if __name__ == "__main__":
    exit(main())