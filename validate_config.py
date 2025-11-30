#!/usr/bin/env python
"""
Validate an Arbodat YAML configuration file.

Usage:
    python validate_config.py <config_file.yml>
"""

import sys
from pathlib import Path

import yaml

from src.arbodat.specifications import CompositeConfigSpecification


def validate_config_file(config_path: str | Path) -> bool:
    """Validate a YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        True if valid, False otherwise.
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return False
    
    # Load YAML configuration
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax in {config_path}")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"Error: Failed to read {config_path}")
        print(f"  {e}")
        return False
    
    # Validate configuration
    spec = CompositeConfigSpecification()
    is_valid = spec.is_satisfied_by(config)
    
    # Print report
    print(f"\nValidation Report for: {config_path}")
    print("=" * 70)
    print(spec.get_report())
    print("=" * 70)
    
    return is_valid


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <config_file.yml>")
        return 1
    
    config_path = sys.argv[1]
    is_valid = validate_config_file(config_path)
    
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
