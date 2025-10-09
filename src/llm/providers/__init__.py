import importlib
import pkgutil
from pathlib import Path

from .provider import ProviderRegistry

Providers: ProviderRegistry = ProviderRegistry()
# Get the directory where this __init__.py file is located
package_dir = Path(__file__).parent

# Automatically import all Python modules in this directory
for module_info in pkgutil.iter_modules([str(package_dir)]):
    if module_info.name not in ["__init__", "strategy"]:
        try:
            importlib.import_module(f".{module_info.name}", package=__name__)
        except ImportError as e:
            print(f"Warning: Could not import strategy module {module_info.name}: {e}")
