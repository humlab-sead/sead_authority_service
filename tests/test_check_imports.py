from pathlib import Path

from scripts.check_imports import find_import_inconsistencies


def _write_python_file(project_root: Path, relative_path: str, content: str) -> None:
    source_file = project_root / relative_path
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(content, encoding="utf-8")


def test_reports_aliases_of_the_same_source_module(tmp_path: Path) -> None:
    _write_python_file(tmp_path, "src/configuration/interface.py", "class ConfigLike:\n    pass\n")
    _write_python_file(
        tmp_path,
        "src/scripts/first.py",
        "from configuration.interface import ConfigLike\n",
    )
    _write_python_file(
        tmp_path,
        "tests/test_imports.py",
        "from src.configuration.interface import ConfigLike\n",
    )

    assert find_import_inconsistencies(tmp_path) == [
        (
            "src/configuration/interface.py",
            {
                "configuration.interface": ["src/scripts/first.py"],
                "src.configuration.interface": ["tests/test_imports.py"],
            },
        )
    ]


def test_does_not_report_different_modules_with_the_same_leaf_name(tmp_path: Path) -> None:
    _write_python_file(tmp_path, "src/identity/models.py", "class Identity:\n    pass\n")
    _write_python_file(tmp_path, "src/mcp/models.py", "class Mcp:\n    pass\n")
    _write_python_file(
        tmp_path,
        "tests/test_models.py",
        "from src.identity import models as identity_models\n" "from src.mcp import models as mcp_models\n",
    )

    assert find_import_inconsistencies(tmp_path) == []


def test_ignores_import_text_in_comments_and_docstrings(tmp_path: Path) -> None:
    _write_python_file(
        tmp_path,
        "src/example.py",
        '"""from configuration.interface import ConfigLike"""\n' "# from src.configuration.interface import ConfigLike\n",
    )

    assert find_import_inconsistencies(tmp_path) == []
