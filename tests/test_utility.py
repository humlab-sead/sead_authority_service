import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.utility import (
    Registry,
    configure_logging,
    create_db_uri,
    dget,
    dotexists,
    dotexpand,
    dotget,
    dotset,
    env2dict,
    get_connection_uri,
    recursive_filter_dict,
    recursive_update,
    replace_env_vars,
    replace_references,
)


class TestRecursiveUpdate:
    """Tests for recursive_update function."""

    def test_simple_update(self):
        """Test simple dictionary update."""
        d1 = {"a": 1, "b": 2}
        d2 = {"c": 3}
        result = recursive_update(d1, d2)
        assert result == {"a": 1, "b": 2, "c": 3}
        assert result is d1  # Should modify original dict

    def test_overwrite_values(self):
        """Test that values are overwritten."""
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 10, "c": 3}
        result = recursive_update(d1, d2)
        assert result == {"a": 10, "b": 2, "c": 3}

    def test_recursive_update_nested(self):
        """Test recursive update of nested dictionaries."""
        d1 = {"a": {"x": 1, "y": 2}, "b": 3}
        d2 = {"a": {"y": 20, "z": 30}, "c": 4}
        result = recursive_update(d1, d2)
        expected = {"a": {"x": 1, "y": 20, "z": 30}, "b": 3, "c": 4}
        assert result == expected

    def test_overwrite_dict_with_non_dict(self):
        """Test that non-dict values overwrite dict values."""
        d1 = {"a": {"x": 1}}
        d2 = {"a": "string"}
        result = recursive_update(d1, d2)
        assert result == {"a": "string"}

    def test_empty_dictionaries(self):
        """Test with empty dictionaries."""
        d1 = {}
        d2 = {"a": 1}
        result = recursive_update(d1, d2)
        assert result == {"a": 1}

        d1 = {"a": 1}
        d2 = {}
        result = recursive_update(d1, d2)
        assert result == {"a": 1}


class TestRecursiveFilterDict:
    """Tests for recursive_filter_dict function."""

    def test_exclude_mode_simple(self):
        """Test exclude mode with simple dictionary."""
        data = {"a": 1, "b": 2, "c": 3}
        filter_keys = {"b"}
        result = recursive_filter_dict(data, filter_keys, "exclude")
        assert result == {"a": 1, "c": 3}

    def test_keep_mode_simple(self):
        """Test keep mode with simple dictionary."""
        data = {"a": 1, "b": 2, "c": 3}
        filter_keys = {"a", "c"}
        result = recursive_filter_dict(data, filter_keys, "keep")
        assert result == {"a": 1, "c": 3}

    def test_exclude_mode_nested(self):
        """Test exclude mode with nested dictionaries."""
        data = {"a": {"x": 1, "y": 2}, "b": 3, "c": {"z": 4}}
        filter_keys = {"y", "b"}
        result = recursive_filter_dict(data, filter_keys, "exclude")
        expected = {"a": {"x": 1}, "c": {"z": 4}}
        assert result == expected

    def test_keep_mode_nested(self):
        """Test keep mode with nested dictionaries."""
        data = {"a": {"x": 1, "y": 2}, "b": 3, "c": {"z": 4}}
        filter_keys = {"a", "x", "c", "z"}
        result = recursive_filter_dict(data, filter_keys, "keep")
        expected = {"a": {"x": 1}, "c": {"z": 4}}
        assert result == expected

    def test_non_dict_values(self):
        """Test that non-dict values are returned as-is."""
        data = {"a": [1, 2, 3], "b": "string", "c": 42}
        filter_keys = {"b"}
        result = recursive_filter_dict(data, filter_keys, "exclude")
        assert result == {"a": [1, 2, 3], "c": 42}

    def test_non_dict_input(self):
        """Test that non-dict input is returned as-is."""
        data = "not a dict"
        filter_keys = {"a"}
        result = recursive_filter_dict(data, filter_keys, "exclude")  # type: ignore
        assert result == "not a dict"

    def test_default_mode_is_exclude(self):
        """Test that default mode is exclude."""
        data = {"a": 1, "b": 2}
        filter_keys = {"b"}
        result = recursive_filter_dict(data, filter_keys)
        assert result == {"a": 1}


class TestDotNotationUtilities:
    """Tests for dot notation utility functions."""

    def test_dotexpand_simple(self):
        """Test dotexpand with simple path."""
        result = dotexpand("a.b.c")
        assert result == ["a.b.c"]

        result = dotexpand(["a.b.c"])
        assert result == ["a.b.c"]

    def test_dotexpand_with_colon(self):
        """Test dotexpand with colon notation."""
        result = dotexpand("a:b:c")
        assert result == ["a.b.c", "a_b_c"]

    def test_dotexpand_with_comma(self):
        """Test dotexpand with comma-separated paths."""
        result = dotexpand("a.b,c.d")
        assert result == ["a.b", "c.d"]

    def test_dotexpand_mixed(self):
        """Test dotexpand with mixed notation."""
        result = dotexpand("a:b,c.d")
        assert result == ["a.b", "a_b", "c.d"]

    def test_dotexpand_with_spaces(self):
        """Test dotexpand removes spaces."""
        result = dotexpand("a.b, c.d")
        assert result == ["a.b", "c.d"]

    def test_dotexpand_empty_parts(self):
        """Test dotexpand handles empty parts."""
        result = dotexpand("a.b,,c.d")
        assert result == ["a.b", "c.d"]

    def test_dotget_simple(self):
        """Test dotget with simple path."""
        data = {"a": {"b": {"c": 42}}}
        result = dotget(data, "a.b.c")
        assert result == 42

    def test_dotget_with_default(self):
        """Test dotget returns default for missing path."""
        data = {"a": {"b": {}}}
        result = dotget(data, "a.b.c", default="not found")
        assert result == "not found"

    def test_dotget_with_colon_notation(self):
        """Test dotget with colon notation."""
        data = {"a": {"b": {"c": 42}}}
        result = dotget(data, "a:b:c")
        assert result == 42

    def test_dotget_with_underscore_fallback(self):
        """Test dotget falls back to underscore notation."""
        data = {"a_b_c": 42}
        result = dotget(data, "a:b:c")
        assert result == 42

    def test_dotget_nonexistent_path(self):
        """Test dotget with nonexistent path."""
        data = {"a": {"b": {}}}
        result = dotget(data, "x.y.z")
        assert result is None

    def test_dotset_simple(self):
        """Test dotset with simple path."""
        data = {}
        result = dotset(data, "a.b.c", 42)
        assert result == {"a": {"b": {"c": 42}}}
        assert result is data  # Should modify original dict

    def test_dotset_with_colon(self):
        """Test dotset with colon notation."""
        data = {}
        dotset(data, "a:b:c", 42)
        assert data == {"a": {"b": {"c": 42}}}

    def test_dotset_overwrite_existing(self):
        """Test dotset overwrites existing values."""
        data = {"a": {"b": {"c": 1}}}
        dotset(data, "a.b.c", 42)
        assert data == {"a": {"b": {"c": 42}}}

    def test_dotset_extend_existing(self):
        """Test dotset extends existing structure."""
        data = {"a": {"b": {"x": 1}}}
        dotset(data, "a.b.c", 42)
        assert data == {"a": {"b": {"x": 1, "c": 42}}}

    def test_dotexists_true(self):
        """Test dotexists returns True for existing path."""
        data = {"a": {"b": {"c": 42}}}
        assert dotexists(data, "a.b.c") is True

    def test_dotexists_false(self):
        """Test dotexists returns False for missing path."""
        data = {"a": {"b": {}}}
        assert dotexists(data, "a.b.c") is False

    def test_dotexists_multiple_paths(self):
        """Test dotexists with multiple paths."""
        data = {"a": {"b": {"c": 42}}}
        assert dotexists(data, "x.y.z", "a.b.c") is True
        assert dotexists(data, "x.y.z", "p.q.r") is False

    def test_dget_simple(self):
        """Test dget with simple usage."""
        data = {"a": {"b": {"c": 42}}}
        result = dget(data, "a.b.c")
        assert result == 42

    def test_dget_with_default(self):
        """Test dget returns default for missing path."""
        data = {"a": {"b": {}}}
        result = dget(data, "a.b.c", default="not found")
        assert result == "not found"

    def test_dget_multiple_paths(self):
        """Test dget tries multiple paths."""
        data = {"a_b_c": 42}
        result = dget(data, "a.b.c", "a:b:c")
        assert result == 42

    def test_dget_none_path(self):
        """Test dget with None path."""
        data = {"a": 1}
        result = dget(data, None, default="default")  # type: ignore
        assert result == "default"

    def test_dget_empty_data(self):
        """Test dget with empty data."""
        result = dget({}, "a.b.c", default="default")
        assert result == "default"


class TestEnv2Dict:
    """Tests for env2dict function."""

    def test_env2dict_simple(self):
        """Test env2dict with simple environment variables."""
        with patch.dict(os.environ, {"APA_A_B": "value1", "APA_C_D": "value2"}):
            result = env2dict("APA")
            expected = {"a": {"b": "value1"}, "c": {"d": "value2"}}
            assert result == expected

    def test_env2dict_with_existing_data(self):
        """Test env2dict with existing data dictionary."""
        with patch.dict(os.environ, {"APA_A_B": "value1"}):
            data = {"existing": "value"}
            result = env2dict("APA", data)
            expected = {"existing": "value", "a": {"b": "value1"}}
            assert result == expected

    def test_env2dict_no_prefix_match(self):
        """Test env2dict when no environment variables match prefix."""
        with patch.dict(os.environ, {"OTHER_A_B": "value1"}):
            result = env2dict("APA")
            assert result == {}

    def test_env2dict_empty_prefix(self):
        """Test env2dict with empty prefix."""
        data = {"existing": "value"}
        result = env2dict("", data)
        assert result == {"existing": "value"}

    def test_env2dict_case_sensitivity(self):
        """Test env2dict case handling."""
        with patch.dict(os.environ, {"APA_A_B": "value1"}):
            result = env2dict("apa")
            expected = {"a": {"b": "value1"}}
            assert result == expected

    def test_env2dict_no_lower_key(self):
        """Test env2dict without lowering keys."""
        with patch.dict(os.environ, {"APA_A_B": "value1"}):
            result = env2dict("APA", lower_key=False)
            expected = {"A": {"B": "value1"}}
            assert result == expected


class TestConfigureLogging:
    """Tests for configure_logging function."""

    @patch("src.utility.logger")
    def test_configure_logging_no_opts(self, mock_logger):
        """Test configure_logging with no options."""
        configure_logging(None)
        mock_logger.remove.assert_called_once()
        mock_logger.add.assert_called_once_with(
            sys.stdout,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        )

    @patch("src.utility.logger")
    def test_configure_logging_with_stdout(self, mock_logger):
        """Test configure_logging with stdout handler."""
        opts = {"handlers": [{"sink": "sys.stdout", "level": "DEBUG"}]}
        configure_logging(opts)
        mock_logger.configure.assert_called_once()
        # Check that sys.stdout was substituted
        handlers = mock_logger.configure.call_args[1]["handlers"]
        assert handlers[0]["sink"] is sys.stdout

    @patch("src.utility.logger")
    @patch("src.utility.datetime")
    def test_configure_logging_with_file(self, mock_datetime, mock_logger):
        """Test configure_logging with file handler."""
        mock_datetime.now.return_value.strftime.return_value = "20231201_120000"

        opts = {"folder": "test_logs", "handlers": [{"sink": "test.log", "level": "ERROR"}]}
        configure_logging(opts)

        handlers = mock_logger.configure.call_args[1]["handlers"]
        expected_path = os.path.join("test_logs", "20231201_120000_test.log")
        assert handlers[0]["sink"] == expected_path

    @patch("src.utility.logger")
    def test_configure_logging_no_sink(self, mock_logger):
        """Test configure_logging with handler missing sink."""
        opts = {"handlers": [{"level": "DEBUG"}]}  # No sink
        configure_logging(opts)
        # Should not call configure since handler has no sink
        mock_logger.configure.assert_called_once_with(handlers=opts["handlers"])


class TestRegistry:
    """Tests for Registry class."""

    def setup_method(self):
        """Clear registry before each test."""
        Registry.items = {}

    def test_register_function(self):
        """Test registering a function."""

        @Registry.register(key="test_func")
        def test_function():
            return "test_result"

        assert Registry.is_registered("test_func")
        fx = Registry.get("test_func")
        assert fx is not None
        assert fx() == "test_result"

    def test_register_with_function_type(self):
        """Test registering with function type (calls function)."""

        @Registry.register(key="test_func", type="function")
        def test_function():
            return "test_result"

        assert Registry.is_registered("test_func")
        assert Registry.get("test_func") == "test_result"

    def test_register_without_key(self):
        """Test registering without explicit key (uses function name)."""

        @Registry.register()
        def my_function():
            return "result"

        assert Registry.is_registered("my_function")
        fx = Registry.get("my_function")

        assert fx is not None
        assert fx() == "result"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key raises ValueError."""
        with pytest.raises(KeyError, match="preprocessor nonexistent is not registered"):
            Registry.get("nonexistent")

    def test_is_registered_false(self):
        """Test is_registered returns False for nonexistent key."""
        assert Registry.is_registered("nonexistent") is False

    def test_register_class(self):
        """Test registering a class."""

        @Registry.register(key="test_class")
        class TestClass:  # pylint: disable=unused-variable
            def method(self):
                return "class_result"

        assert Registry.is_registered("test_class")
        cls = Registry.get("test_class")
        assert cls is not None
        instance = cls()
        assert instance.method() == "class_result"


class TestReplaceEnvVars:
    """Tests for replace_env_vars function."""

    def test_replace_env_vars_simple_string(self):
        """Test replace_env_vars with simple environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = replace_env_vars("${TEST_VAR}")
            assert result == "test_value"

    def test_replace_env_vars_nonexistent_var(self):
        """Test replace_env_vars with nonexistent environment variable."""
        # Clear any existing TEST_NONEXISTENT var
        with patch.dict(os.environ, {}, clear=True):
            result = replace_env_vars("${TEST_NONEXISTENT}")
            assert result == ""

    def test_replace_env_vars_regular_string(self):
        """Test replace_env_vars with regular string (no replacement)."""
        result = replace_env_vars("regular_string")
        assert result == "regular_string"

    def test_replace_env_vars_partial_pattern(self):
        """Test replace_env_vars with partial patterns (no replacement)."""
        result = replace_env_vars("${INCOMPLETE")
        assert result == "${INCOMPLETE"

        result = replace_env_vars("INCOMPLETE}")
        assert result == "INCOMPLETE}"

        result = replace_env_vars("$MISSING_BRACES")
        assert result == "$MISSING_BRACES"

    def test_replace_env_vars_empty_var_name(self):
        """Test replace_env_vars with empty variable name."""
        result = replace_env_vars("${}")
        assert result == ""

    def test_replace_env_vars_dict_simple(self):
        """Test replace_env_vars with simple dictionary."""
        with patch.dict(os.environ, {"DB_HOST": "localhost", "DB_PORT": "5432"}):
            data = {"host": "${DB_HOST}", "port": "${DB_PORT}", "name": "myapp"}
            result = replace_env_vars(data)
            expected = {"host": "localhost", "port": "5432", "name": "myapp"}
            assert result == expected

    def test_replace_env_vars_nested_dict(self):
        """Test replace_env_vars with nested dictionary."""
        with patch.dict(os.environ, {"DB_HOST": "localhost", "API_KEY": "secret123"}):
            data = {"database": {"host": "${DB_HOST}", "credentials": {"api_key": "${API_KEY}"}}, "app": {"name": "test_app"}}
            result = replace_env_vars(data)
            expected = {"database": {"host": "localhost", "credentials": {"api_key": "secret123"}}, "app": {"name": "test_app"}}
            assert result == expected

    def test_replace_env_vars_list_simple(self):
        """Test replace_env_vars with simple list."""
        with patch.dict(os.environ, {"SERVER1": "server1.com", "SERVER2": "server2.com"}):
            data = ["${SERVER1}", "${SERVER2}", "hardcoded.com"]
            result = replace_env_vars(data)
            expected = ["server1.com", "server2.com", "hardcoded.com"]
            assert result == expected

    def test_replace_env_vars_nested_list(self):
        """Test replace_env_vars with nested list structure."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8080"}):
            data = [{"server": "${HOST}", "port": "${PORT}"}, {"server": "remote.com", "port": "9090"}, ["${HOST}", "static_value"]]
            result = replace_env_vars(data)
            expected = [{"server": "localhost", "port": "8080"}, {"server": "remote.com", "port": "9090"}, ["localhost", "static_value"]]
            assert result == expected

    def test_replace_env_vars_mixed_data_types(self):
        """Test replace_env_vars with mixed data types."""
        with patch.dict(os.environ, {"STRING_VAR": "test_string", "NUMBER_VAR": "42"}):
            data = {
                "string": "${STRING_VAR}",
                "number": 123,
                "boolean": True,
                "none_value": None,
                "env_number": "${NUMBER_VAR}",
                "list": [1, "${STRING_VAR}", True, None],
                "nested": {"env_val": "${STRING_VAR}", "regular_val": "unchanged"},
            }
            result = replace_env_vars(data)
            expected = {
                "string": "test_string",
                "number": 123,
                "boolean": True,
                "none_value": None,
                "env_number": "42",
                "list": [1, "test_string", True, None],
                "nested": {"env_val": "test_string", "regular_val": "unchanged"},
            }
            assert result == expected

    def test_replace_env_vars_complex_nested_structure(self):
        """Test replace_env_vars with complex nested structure."""
        with patch.dict(os.environ, {"DB_HOST": "db.example.com", "DB_USER": "admin", "API_TOKEN": "abc123", "LOG_LEVEL": "INFO"}):
            data = {
                "services": [
                    {"name": "database", "config": {"host": "${DB_HOST}", "auth": {"username": "${DB_USER}", "token": "${API_TOKEN}"}}},
                    {"name": "logger", "config": {"level": "${LOG_LEVEL}", "outputs": ["console", "file"]}},
                ],
                "metadata": {"version": "1.0.0", "env_info": "${DB_HOST}"},
            }

            result = replace_env_vars(data)

            expected = {
                "services": [
                    {"name": "database", "config": {"host": "db.example.com", "auth": {"username": "admin", "token": "abc123"}}},
                    {"name": "logger", "config": {"level": "INFO", "outputs": ["console", "file"]}},
                ],
                "metadata": {"version": "1.0.0", "env_info": "db.example.com"},
            }
            assert result == expected

    def test_replace_env_vars_empty_containers(self):
        """Test replace_env_vars with empty containers."""
        result = replace_env_vars({})
        assert result == {}

        result = replace_env_vars([])
        assert result == []

        result = replace_env_vars({"empty_dict": {}, "empty_list": []})
        assert result == {"empty_dict": {}, "empty_list": []}

    def test_replace_env_vars_no_modification_to_original(self):
        """Test that replace_env_vars doesn't modify the original data."""
        with patch.dict(os.environ, {"TEST_VAR": "replaced"}):
            original_data = {"value": "${TEST_VAR}", "nested": {"list": ["${TEST_VAR}", "static"]}}
            original_copy = {"value": "${TEST_VAR}", "nested": {"list": ["${TEST_VAR}", "static"]}}

            result = replace_env_vars(original_data)

            # Original data should be unchanged
            assert original_data == original_copy

            # Result should have replacements
            expected = {"value": "replaced", "nested": {"list": ["replaced", "static"]}}
            assert result == expected

    def test_replace_env_vars_special_characters_in_env_var(self):
        """Test replace_env_vars with special characters in environment variable values."""
        with patch.dict(os.environ, {"SPECIAL_CHARS": "!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"}):
            result = replace_env_vars("${SPECIAL_CHARS}")
            assert result == "!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"

    def test_replace_env_vars_unicode_characters(self):
        """Test replace_env_vars with unicode characters in environment variables."""
        with patch.dict(os.environ, {"UNICODE_VAR": "Hello 世界 🌍 café naïve résumé"}):
            result = replace_env_vars("${UNICODE_VAR}")
            assert result == "Hello 世界 🌍 café naïve résumé"

    def test_replace_env_vars_multiple_vars_in_structure(self):
        """Test replace_env_vars with multiple environment variables."""
        with patch.dict(
            os.environ, {"VAR1": "value1", "VAR2": "value2", "VAR3": "value3", "MISSING_VAR": ""}, clear=True  # This will be missing from environment
        ):
            # Remove MISSING_VAR to test missing behavior
            if "MISSING_VAR" in os.environ:
                del os.environ["MISSING_VAR"]

            data = {
                "present1": "${VAR1}",
                "present2": "${VAR2}",
                "present3": "${VAR3}",
                "missing": "${MISSING_VAR}",
                "mixed_list": ["${VAR1}", "${MISSING_VAR}", "static", "${VAR2}"],
            }

            result = replace_env_vars(data)
            expected = {
                "present1": "value1",
                "present2": "value2",
                "present3": "value3",
                "missing": "",  # Missing vars return empty string
                "mixed_list": ["value1", "", "static", "value2"],
            }
            assert result == expected


class TestDatabaseUtilities:
    """Tests for database utility functions."""

    def test_create_db_uri(self):
        """Test create_db_uri function."""
        uri = create_db_uri(host="localhost", port=5432, user="testuser", dbname="testdb")
        expected = "postgresql://testuser@localhost:5432/testdb"
        assert uri == expected

    def test_create_db_uri_string_port(self):
        """Test create_db_uri with string port."""
        uri = create_db_uri(host="localhost", port="5432", user="testuser", dbname="testdb")
        expected = "postgresql://testuser@localhost:5432/testdb"
        assert uri == expected

    def test_get_connection_uri(self):
        """Test get_connection_uri function."""
        mock_connection = MagicMock()
        mock_connection.get_dsn_parameters.return_value = {"user": "testuser", "host": "localhost", "port": "5432", "dbname": "testdb"}

        uri = get_connection_uri(mock_connection)
        expected = "postgresql://testuser@localhost:5432/testdb"
        assert uri == expected

    def test_get_connection_uri_missing_params(self):
        """Test get_connection_uri with missing parameters."""
        mock_connection = MagicMock()
        mock_connection.get_dsn_parameters.return_value = {"user": None, "host": "localhost", "port": "5432", "dbname": "testdb"}

        uri = get_connection_uri(mock_connection)
        expected = "postgresql://None@localhost:5432/testdb"
        assert uri == expected


# Integration tests
class TestReplaceReferences:
    """Tests for replace_references and _replace_references functions."""

    def test_replace_references_simple_string_reference(self):
        """Test replace_references with simple string reference."""
        data = {"target": "value123", "ref": "include:target"}
        result = replace_references(data)
        assert result == {"target": "value123", "ref": "value123"}

    def test_replace_references_nested_path_reference(self):
        """Test replace_references with nested dotpath reference."""
        data = {
            "config": {"database": {"host": "localhost", "port": 5432}},
            "db_host": "include:config.database.host",
            "db_port": "include:config.database.port",
        }
        result = replace_references(data)
        assert result == {"config": {"database": {"host": "localhost", "port": 5432}}, "db_host": "localhost", "db_port": 5432}

    def test_replace_references_colon_notation(self):
        """Test replace_references with colon notation in path."""
        data = {"app": {"settings": {"timeout": 30}}, "ref": "include:app:settings:timeout"}
        result = replace_references(data)
        assert result == {"app": {"settings": {"timeout": 30}}, "ref": 30}

    def test_replace_references_missing_path(self):
        """Test replace_references with nonexistent path (returns original string)."""
        data = {"value": "test", "ref": "include:nonexistent.path"}
        result = replace_references(data)
        assert result == {"value": "test", "ref": "include:nonexistent.path"}

    def test_replace_references_non_reference_string(self):
        """Test replace_references leaves non-reference strings unchanged."""
        data = {"regular": "just a string", "not_ref": "something:include", "also_not": "includetest"}
        result = replace_references(data)
        assert result == {"regular": "just a string", "not_ref": "something:include", "also_not": "includetest"}

    def test_replace_references_dict_structure(self):
        """Test replace_references with nested dict structure."""
        data = {"base": {"value": "original"}, "nested": {"config": {"ref": "include:base.value"}}}
        result = replace_references(data)
        assert result == {"base": {"value": "original"}, "nested": {"config": {"ref": "original"}}}

    def test_replace_references_list_structure(self):
        """Test replace_references with list containing references."""
        # Note: dotget doesn't support numeric indices, so list item references won't resolve
        data = {"values": ["a", "b", "c"], "whole_list": "include:values", "refs": ["include:whole_list", "static"]}
        result = replace_references(data)
        assert result == {"values": ["a", "b", "c"], "whole_list": ["a", "b", "c"], "refs": [["a", "b", "c"], "static"]}

    def test_replace_references_mixed_list_and_dict(self):
        """Test replace_references with mixed list and dict structures."""
        # dotget doesn't support numeric indices, so we reference the whole list instead
        data = {
            "primary_server": {"name": "server1", "host": "host1.com"},
            "servers": [{"name": "server1", "host": "host1.com"}, {"name": "server2", "host": "host2.com"}],
            "primary_host": "include:primary_server.host",
        }
        result = replace_references(data)
        assert result == {
            "primary_server": {"name": "server1", "host": "host1.com"},
            "servers": [{"name": "server1", "host": "host1.com"}, {"name": "server2", "host": "host2.com"}],
            "primary_host": "host1.com",
        }

    def test_replace_references_recursive_resolution(self):
        """Test replace_references with reference pointing to another reference."""
        data = {"value": "final_value", "ref1": "include:value", "ref2": "include:ref1"}
        result = replace_references(data)
        # ref2 should resolve to ref1's value, which resolves to "final_value"
        assert result == {"value": "final_value", "ref1": "final_value", "ref2": "final_value"}

    def test_replace_references_reference_to_dict(self):
        """Test replace_references with reference pointing to dict."""
        data = {"settings": {"timeout": 30, "retries": 3}, "copied": "include:settings"}
        result = replace_references(data)
        assert result == {"settings": {"timeout": 30, "retries": 3}, "copied": {"timeout": 30, "retries": 3}}

    def test_replace_references_reference_to_list(self):
        """Test replace_references with reference pointing to list."""
        data = {"items": [1, 2, 3], "copied_items": "include:items"}
        result = replace_references(data)
        assert result == {"items": [1, 2, 3], "copied_items": [1, 2, 3]}

    def test_replace_references_multiple_refs_to_same_path(self):
        """Test replace_references with multiple references to same path."""
        data = {"source": "shared_value", "ref1": "include:source", "ref2": "include:source", "ref3": "include:source"}
        result = replace_references(data)
        assert result == {"source": "shared_value", "ref1": "shared_value", "ref2": "shared_value", "ref3": "shared_value"}

    def test_replace_references_empty_structures(self):
        """Test replace_references with empty dict and list."""
        result = replace_references({})
        assert result == {}

        result = replace_references([])
        assert result == []

        data = {"empty_dict": {}, "empty_list": [], "ref_to_empty": "include:empty_dict"}
        result = replace_references(data)
        assert result == {"empty_dict": {}, "empty_list": [], "ref_to_empty": {}}

    def test_replace_references_complex_nested_structure(self):
        """Test replace_references with complex nested structure."""
        data = {
            "database": {"primary": {"host": "db1.example.com", "port": 5432}, "replica": {"host": "db2.example.com", "port": 5433}},
            "app": {"db_config": {"main": "include:database.primary", "backup": "include:database.replica.host"}},
            "monitoring": {"targets": ["include:database.primary.host", "include:database.replica.host"]},
        }
        result = replace_references(data)
        expected = {
            "database": {"primary": {"host": "db1.example.com", "port": 5432}, "replica": {"host": "db2.example.com", "port": 5433}},
            "app": {"db_config": {"main": {"host": "db1.example.com", "port": 5432}, "backup": "db2.example.com"}},
            "monitoring": {"targets": ["db1.example.com", "db2.example.com"]},
        }
        assert result == expected

    def test_replace_references_deep_nesting(self):
        """Test replace_references with deeply nested path."""
        data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}, "ref": "include:level1.level2.level3.level4.value"}
        result = replace_references(data)
        assert result == {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}, "ref": "deep"}

    def test_replace_references_underscore_fallback(self):
        """Test replace_references with underscore notation fallback."""
        data = {"app_config_value": 42, "ref": "include:app:config:value"}
        result = replace_references(data)
        assert result == {"app_config_value": 42, "ref": 42}

    def test_replace_references_mixed_data_types(self):
        """Test replace_references with various data types."""
        data = {
            "string": "text",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "none_value": None,
            "ref_string": "include:string",
            "ref_number": "include:number",
            "ref_float": "include:float",
            "ref_boolean": "include:boolean",
            "ref_none": "include:none_value",
        }
        result = replace_references(data)
        expected = {
            "string": "text",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "none_value": None,
            "ref_string": "text",
            "ref_number": 123,
            "ref_float": 45.67,
            "ref_boolean": True,
            # Note: When the referenced value is None, dotget returns None as default,
            # and _replace_references returns the original string if ref_value is None
            "ref_none": "include:none_value",
        }
        assert result == expected

    def test_replace_references_does_not_modify_original(self):
        """Test that replace_references doesn't modify the original data."""
        original_data = {"value": "original", "ref": "include:value"}
        original_copy = {"value": "original", "ref": "include:value"}

        result = replace_references(original_data)

        # Original data should be unchanged
        assert original_data == original_copy

        # Result should have replacements
        assert result == {"value": "original", "ref": "original"}


class TestIntegration:
    """Integration tests combining multiple utility functions."""

    def test_dotset_and_dotget_integration(self):
        """Test dotset and dotget work together."""
        data = {}
        dotset(data, "config:database:host", "localhost")
        dotset(data, "config:database:port", 5432)

        assert dotget(data, "config.database.host") == "localhost"
        assert dotget(data, "config:database:port") == 5432

    def test_recursive_update_and_filter_integration(self):
        """Test recursive_update and recursive_filter_dict work together."""
        base_config = {"database": {"host": "localhost", "port": 5432}, "logging": {"level": "INFO"}}

        user_config = {"database": {"port": 3306, "name": "mydb"}, "cache": {"enabled": True}}

        # Update configuration
        merged = recursive_update(base_config.copy(), user_config)

        # Filter out sensitive info
        filtered = recursive_filter_dict(merged, {"port"}, "exclude")

        expected = {"database": {"host": "localhost", "name": "mydb"}, "logging": {"level": "INFO"}, "cache": {"enabled": True}}
        assert filtered == expected

    def test_env2dict_and_dotget_integration(self):
        """Test env2dict and dotget work together."""
        with patch.dict(os.environ, {"APP_DB_HOST": "localhost", "APP_DB_PORT": "5432"}):
            config = env2dict("APP")

            assert dotget(config, "db.host") == "localhost"
            assert dotget(config, "db.port") == "5432"
            assert dget(config, "db:host", "db.host") == "localhost"

    def test_replace_references_and_replace_env_vars_integration(self):
        """Test replace_references works after replace_env_vars."""
        with patch.dict(os.environ, {"DB_HOST": "env-host.example.com"}):
            # First replace env vars, then references
            data = {"env_value": "${DB_HOST}", "reference": "include:env_value"}

            step1 = replace_env_vars(data)
            assert step1 == {"env_value": "env-host.example.com", "reference": "include:env_value"}

            step2 = replace_references(step1)
            assert step2 == {"env_value": "env-host.example.com", "reference": "env-host.example.com"}
