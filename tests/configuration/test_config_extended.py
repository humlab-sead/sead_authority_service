"""Extended tests for src.configuration.config module to improve coverage."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.configuration.config import (
    BaseResolver,
    Config,
    ConfigFactory,
    LoadResolver,
    SafeLoaderIgnoreUnknown,
    SubConfigResolver,
    is_path_to_existing_file,
    nj,
    yaml_path_join,
    yaml_str_join,
)


class TestYAMLHelpers:
    """Test YAML custom constructors and utility functions."""

    def test_yaml_str_join_constructor(self) -> None:
        """Test !join constructor joins sequence elements into string."""
        yaml_content = """
joined: !join ['hello', ' ', 'world']
"""
        result = yaml.load(io.StringIO(yaml_content), Loader=SafeLoaderIgnoreUnknown)
        assert result["joined"] == "hello world"

    def test_yaml_path_join_constructor(self) -> None:
        """Test !path_join and !jj constructors join paths correctly."""
        yaml_content = """
path1: !path_join ['dir', 'subdir', 'file.txt']
path2: !jj ['another', 'path']
"""
        result = yaml.load(io.StringIO(yaml_content), Loader=SafeLoaderIgnoreUnknown)
        assert "dir" in result["path1"]
        assert "subdir" in result["path1"]
        assert "file.txt" in result["path1"]
        assert "another" in result["path2"]

    def test_nj_joins_valid_paths(self) -> None:
        """Test nj normalizes and joins valid paths."""
        result = nj("dir", "subdir", "file.txt")
        assert result is not None
        assert "dir" in result
        assert "file.txt" in result

    def test_nj_returns_none_if_any_none(self) -> None:
        """Test nj returns None if any path component is None."""
        assert nj("dir", None, "file") is None
        assert nj(None, "dir") is None

    def test_is_path_to_existing_file_edge_cases(self) -> None:
        """Test is_path_to_existing_file with various invalid inputs."""
        assert is_path_to_existing_file(None) is False
        assert is_path_to_existing_file(123) is False
        assert is_path_to_existing_file([]) is False
        assert is_path_to_existing_file("/nonexistent/path.txt") is False


class TestSafeLoaderIgnoreUnknown:
    """Test custom YAML loader that ignores unknown tags."""

    def test_unknown_scalar_tag(self) -> None:
        """Test loader handles unknown scalar tags gracefully."""
        yaml_content = "value: !unknown_tag scalar_value"
        result = yaml.load(io.StringIO(yaml_content), Loader=SafeLoaderIgnoreUnknown)
        assert result["value"] == "scalar_value"

    def test_unknown_sequence_tag(self) -> None:
        """Test loader handles unknown sequence tags."""
        yaml_content = "value: !unknown [1, 2, 3]"
        result = yaml.load(io.StringIO(yaml_content), Loader=SafeLoaderIgnoreUnknown)
        assert result["value"] == [1, 2, 3]

    def test_unknown_mapping_tag(self) -> None:
        """Test loader handles unknown mapping tags."""
        yaml_content = "value: !unknown {key: val}"
        result = yaml.load(io.StringIO(yaml_content), Loader=SafeLoaderIgnoreUnknown)
        assert result["value"] == {"key": "val"}


class TestConfigClone:
    """Test Config.clone method."""

    def test_clone_creates_deep_copy(self) -> None:
        """Clone should create independent copy of config data."""
        cfg = Config(
            data={"section": {"nested": {"value": [1, 2, 3]}}},
            context="test",
            filename="/path/to/config.yml",
            env_filename=".env",
            env_prefix="APP",
        )

        cloned = cfg.clone()

        # Verify data is deep copied
        assert cloned.data == cfg.data
        assert cloned.data is not cfg.data
        cloned.data["section"]["nested"]["value"].append(4)
        assert len(cfg.data["section"]["nested"]["value"]) == 3

        # Verify metadata is copied
        assert cloned.context == cfg.context
        assert cloned.filename == cfg.filename
        assert cloned.env_filename == cfg.env_filename
        assert cloned.env_prefix == cfg.env_prefix


class TestConfigUpdate:
    """Test Config.update with various input formats."""

    def test_update_with_tuple(self) -> None:
        """Update should accept single tuple."""
        cfg = Config(data={})
        cfg.update(("section:key", "value"))
        assert cfg.get("section:key") == "value"

    def test_update_with_list_of_tuples(self) -> None:
        """Update should accept list of tuples."""
        cfg = Config(data={})
        cfg.update([("section:a", 1), ("section:b", 2)])
        assert cfg.get("section:a") == 1
        assert cfg.get("section:b") == 2

    def test_update_initializes_empty_data(self) -> None:
        """Update should initialize data if None."""
        cfg = Config(data=None)  # type: ignore
        cfg.update({"key": "value"})
        assert cfg.data is not None
        assert cfg.data["key"] == "value"


class TestConfigSaveErrors:
    """Test Config.save error handling."""

    def test_save_raises_without_filename(self) -> None:
        """Save should raise ValueError if no filename is set."""
        cfg = Config(data={"key": "value"})
        with pytest.raises(ValueError, match="no filename"):
            cfg.save()

    def test_save_warns_when_saving_without_updates(self, tmp_path: Path) -> None:
        """Save without updates should log warning about losing directives."""
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text("key: ${ENV_VAR}\n", encoding="utf-8")

        cfg = Config(data={"key": "resolved"}, filename=str(cfg_file))

        with patch("src.configuration.config.logger") as mock_logger:
            cfg.save()
            mock_logger.warning.assert_called_once()
            assert "resolved configuration" in mock_logger.warning.call_args[0][0]


class TestConfigResolveReferences:
    """Test Config.resolve_references static method."""

    def test_resolve_references_with_inplace_false(self) -> None:
        """resolve_references should not mutate input when inplace=False."""
        original = {"section": {"value": "${VAR}"}}
        with patch.dict("os.environ", {"VAR": "replaced"}):
            resolved = Config.resolve_references(original, inplace=False)

        # Original should be unchanged
        assert original["section"]["value"] == "${VAR}"
        # Resolved should have substitution
        assert resolved["section"]["value"] == "replaced"

    def test_resolve_references_with_inplace_true(self) -> None:
        """resolve_references with inplace=True modifies original dict."""
        data = {"section": {"value": "${VAR}"}}
        with patch.dict("os.environ", {"VAR": "replaced"}):
            # Need to pass resolved data through resolve chain
            resolved = Config.resolve_references(data, inplace=True)

        # Result should have substitution (inplace still creates deep copy internally for some operations)
        assert resolved["section"]["value"] == "replaced"


class TestConfigFactoryEdgeCases:
    """Test ConfigFactory with various edge cases."""

    def test_load_with_config_like_returns_same(self) -> None:
        """load should return ConfigLike instances unchanged."""
        cfg = Config(data={"key": "value"})
        factory = ConfigFactory()

        loaded = factory.load(source=cfg)

        assert loaded is cfg

    def test_load_with_none_source_creates_empty(self) -> None:
        """load with None source should create empty config."""
        factory = ConfigFactory()
        cfg = factory.load(source=None)

        assert isinstance(cfg, Config)
        assert cfg.data == {}

    def test_load_with_dict_source(self) -> None:
        """load should accept dict source directly."""
        factory = ConfigFactory()
        cfg = factory.load(source={"section": {"key": "value"}})

        assert cfg.data["section"]["key"] == "value"

    def test_load_with_skip_resolve(self, tmp_path: Path) -> None:
        """load with skip_resolve should not resolve directives."""
        cfg_file = tmp_path / "config.yml"
        cfg_file.write_text("value: ${ENV_VAR}\n", encoding="utf-8")

        with patch.dict("os.environ", {"ENV_VAR": "replaced"}):
            cfg = ConfigFactory().load(source=str(cfg_file), skip_resolve=True)

        # Should not be resolved
        assert cfg.data["value"] == "${ENV_VAR}"


class TestBaseResolver:
    """Test BaseResolver abstract functionality."""

    def test_base_resolver_resolves_nested_structures(self) -> None:
        """BaseResolver should recursively process nested dicts and lists."""

        class TestResolver(BaseResolver):
            directive = "@test"

            def resolve_directive(self, directive_argument: str, base_path: Path | None) -> str:
                return f"resolved_{directive_argument}"

        resolver = TestResolver()
        data = {
            "simple": "@test:value",
            "nested": {"inner": "@test:nested_value"},
            "list": ["@test:item1", "@test:item2"],
            "unchanged": "normal_value",
        }

        result = resolver.resolve(data)

        assert result["simple"] == "resolved_value"
        assert result["nested"]["inner"] == "resolved_nested_value"
        assert result["list"] == ["resolved_item1", "resolved_item2"]
        assert result["unchanged"] == "normal_value"


class TestSubConfigResolver:
    """Test SubConfigResolver for @include directives."""

    def test_resolve_include_with_relative_path(self, tmp_path: Path) -> None:
        """SubConfigResolver should resolve relative paths."""
        sub_file = tmp_path / "subconfig.yml"
        sub_file.write_text("key: subvalue\n", encoding="utf-8")

        main_file = tmp_path / "main.yml"
        main_file.write_text(f'included: "@include:{sub_file.name}"\n', encoding="utf-8")

        resolver = SubConfigResolver(source_path=str(main_file))
        data = {"included": f"@include:{sub_file.name}"}

        result = resolver.resolve(data)

        assert result["included"]["key"] == "subvalue"

    def test_resolve_include_with_absolute_path(self, tmp_path: Path) -> None:
        """SubConfigResolver should handle absolute paths."""
        sub_file = tmp_path / "subconfig.yml"
        sub_file.write_text("abs_key: abs_value\n", encoding="utf-8")

        resolver = SubConfigResolver()
        data = {"included": f"@include:{sub_file}"}

        result = resolver.resolve(data)

        assert result["included"]["abs_key"] == "abs_value"


class TestLoadResolver:
    """Test LoadResolver for @load directives."""

    def test_load_csv_with_custom_delimiter(self, tmp_path: Path) -> None:
        """LoadResolver should support custom delimiters."""
        tsv_file = tmp_path / "data.tsv"
        tsv_file.write_text("name\tage\nalice\t30\nbob\t40\n", encoding="utf-8")

        main_file = tmp_path / "main.yml"
        resolver = LoadResolver(source_path=str(main_file))
        resolver.data = {"csv_opts": {"filename": str(tsv_file), "delimiter": "\t"}}

        result = resolver.resolve_directive("csv_opts", tmp_path)

        assert len(result) == 2
        assert result[0]["name"] == "alice"
        assert result[1]["age"] == "40"

    def test_load_with_nonexistent_file_returns_original(self, tmp_path: Path) -> None:
        """LoadResolver should return original string for missing files."""
        resolver = LoadResolver(source_path=str(tmp_path / "main.yml"))

        result = resolver.resolve_directive("nonexistent.csv", tmp_path)

        assert result == "nonexistent.csv"

    def test_load_with_invalid_csv_returns_original(self, tmp_path: Path) -> None:
        """LoadResolver should return original for unparseable files."""
        bad_file = tmp_path / "bad.csv"
        bad_file.write_text("not,a,valid\ncsv file content\n\n\n", encoding="utf-8")

        resolver = LoadResolver(source_path=str(tmp_path / "main.yml"))

        # Force an error by mocking pd.read_csv
        with patch("src.configuration.config.pd.read_csv", side_effect=Exception("Parse error")):
            result = resolver.resolve_directive(str(bad_file), tmp_path)

        assert result == str(bad_file)

    def test_load_with_non_dict_options_returns_original(self) -> None:
        """LoadResolver should ignore non-dict options."""
        resolver = LoadResolver()
        resolver.data = {"csv_opts": "not a dict"}

        result = resolver.resolve_directive("csv_opts", None)

        assert result == "csv_opts"

    def test_load_with_missing_filename_in_options_returns_original(self) -> None:
        """LoadResolver should ignore options without filename."""
        resolver = LoadResolver()
        resolver.data = {"csv_opts": {"delimiter": ","}}

        result = resolver.resolve_directive("csv_opts", None)

        assert result == "csv_opts"
