#!/usr/bin/env python3
"""
Script to automatically convert relative imports to absolute imports.
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path: Path, project_root: Path):
    """Fix imports in a single file."""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Get relative path from project root
        rel_path = file_path.relative_to(project_root)
        
        # Convert specific problematic imports
        fixes = [
            # configuration.inject -> src.configuration.inject
            (r'from\s+configuration\.inject\s+import', 'from src.configuration.inject import'),
            (r'import\s+configuration\.inject', 'import src.configuration.inject'),
            
            # Add more patterns as needed
            (r'from\s+llm\.providers\s+import', 'from src.llm.providers import'),
            (r'from\s+strategies\.(\w+)\s+import', r'from src.strategies.\1 import'),
        ]
        
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {rel_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"
    
    fixed_count = 0
    
    # Fix imports in src/ and tests/
    for directory in [src_dir, tests_dir]:
        if directory.exists():
            for py_file in directory.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                    
                if fix_imports_in_file(py_file, project_root):
                    fixed_count += 1
    
    if fixed_count > 0:
        print(f"\n🔧 Fixed imports in {fixed_count} files")
        print("💡 Run your tests to make sure everything still works!")
    else:
        print("✅ No import fixes needed")

if __name__ == "__main__":
    main()