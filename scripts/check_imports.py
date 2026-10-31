#!/usr/bin/env python3
"""Check whether repository modules are imported through multiple paths."""

import ast
import sys
from collections import defaultdict
from pathlib import Path

IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", "build", "dist", "node_modules", "venv"}


def _module_name_for_file(source_file: Path, project_root: Path) -> str:
    parts = source_file.relative_to(project_root).parts
    prefix: tuple[str, ...] = ()
    if parts and parts[0] == "src":
        prefix = ("src",)
        parts = parts[1:]

    if parts and parts[-1] == "__init__.py":
        module_parts = parts[:-1]
    elif parts:
        module_parts = (*parts[:-1], Path(parts[-1]).stem)
    else:
        module_parts = ()

    return ".".join((*prefix, *module_parts))


def _resolve_module_path(module_name: str, project_root: Path) -> Path | None:
    parts = tuple(module_name.split("."))
    if not parts or any(not part for part in parts):
        return None

    if parts[0] == "src":
        search_roots = (project_root / "src",)
        module_parts = parts[1:]
    else:
        search_roots = (project_root, project_root / "src")
        module_parts = parts

    for search_root in search_roots:
        if module_parts:
            relative_path = Path(*module_parts)
            package_directory = search_root / relative_path
            candidates = (
                package_directory / "__init__.py",
                relative_path.with_suffix(".py"),
            )
            for candidate in candidates:
                source_file = candidate if candidate.is_absolute() else search_root / candidate
                if source_file.is_file():
                    return source_file.resolve()
            if package_directory.is_dir():
                return package_directory.resolve()
        else:
            init_file = search_root / "__init__.py"
            if init_file.is_file():
                return init_file.resolve()
            if search_root.is_dir():
                return search_root.resolve()

    return None


def _absolute_import_base(node: ast.ImportFrom, source_file: Path, project_root: Path) -> str | None:
    if node.level == 0:
        return node.module

    current_module = _module_name_for_file(source_file, project_root)
    package_parts = current_module.split(".") if current_module else []
    if source_file.name != "__init__.py" and package_parts:
        package_parts.pop()

    levels_to_remove = node.level - 1
    if levels_to_remove > len(package_parts):
        return None
    if levels_to_remove:
        package_parts = package_parts[:-levels_to_remove]
    if node.module:
        package_parts.extend(node.module.split("."))

    return ".".join(package_parts) or None


def _imported_module_names(node: ast.Import | ast.ImportFrom, source_file: Path, project_root: Path) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}

    base_name = _absolute_import_base(node, source_file, project_root)
    if not base_name:
        return set()

    base_path = _resolve_module_path(base_name, project_root)
    imported_names: set[str] = set()
    for alias in node.names:
        if alias.name == "*":
            continue
        submodule_name = f"{base_name}.{alias.name}"
        if _resolve_module_path(submodule_name, project_root):
            imported_names.add(submodule_name)
        elif base_path:
            imported_names.add(base_name)

    if not imported_names and base_path:
        imported_names.add(base_name)

    return imported_names


def find_import_inconsistencies(project_root: str | Path) -> list[tuple[str, dict[str, list[str]]]]:
    """Return repository modules imported through more than one module path."""
    root = Path(project_root).resolve()
    module_imports: defaultdict[Path, defaultdict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for source_file in root.rglob("*.py"):
        if IGNORED_DIRECTORIES.intersection(source_file.relative_to(root).parts):
            continue

        syntax_tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
        importing_file = source_file.relative_to(root).as_posix()
        for node in ast.walk(syntax_tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for import_name in _imported_module_names(node, source_file, root):
                module_path = _resolve_module_path(import_name, root)
                if module_path:
                    module_imports[module_path][import_name].add(importing_file)

    inconsistencies: list[tuple[str, dict[str, list[str]]]] = []
    for module_path, import_paths in module_imports.items():
        if len(import_paths) < 2:
            continue
        try:
            display_path = module_path.relative_to(root).as_posix()
        except ValueError:
            display_path = str(module_path)
        path_groups = {name: sorted(files) for name, files in sorted(import_paths.items())}
        inconsistencies.append((display_path, path_groups))

    return sorted(inconsistencies)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    try:
        inconsistencies = find_import_inconsistencies(project_root)
    except (OSError, UnicodeError, SyntaxError) as error:
        print(f"ERROR: Could not inspect Python imports: {error}", file=sys.stderr)
        return 2

    if inconsistencies:
        print("Import path inconsistencies found:")
        print("=" * 60)
        for module_path, import_paths in inconsistencies:
            print(f"\nSource module: {module_path}")
            for import_path, files in import_paths.items():
                print(f"  Import path: {import_path}")
                for file_path in files[:3]:
                    print(f"    - {file_path}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more files")
            print()

        print("Use one import path for each source module.")
        return 1

    print("No import path inconsistencies found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
