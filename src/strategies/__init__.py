import importlib
import pkgutil
from pathlib import Path
from typing import Any

package_dir = Path(__file__).parent

StrategySpecification = dict[str, str | dict[str, Any]]


def _import_submodules(package_name: str, package_path: str):
    """Recursively import all submodules of a package."""
    for module_info in pkgutil.iter_modules([package_path]):
        full_name = f"{package_name}.{module_info.name}"
        if module_info.ispkg:
            # Import the package and recurse
            try:
                _ = importlib.import_module(full_name)
                _import_submodules(full_name, str(Path(package_path) / module_info.name))
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"⚠️ Warning: Could not import subpackage {full_name}: {e}")
        else:
            if module_info.name not in ["__init__", "strategy"]:
                try:
                    importlib.import_module(full_name)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"⚠️ Warning: Could not import module {full_name}: {e}")


_import_submodules(__name__, str(package_dir))
