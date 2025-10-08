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
        result = recursive_filter_dict(data, filter_keys, "exclude")
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
        assert dotexists(data, ["x.y.z"], ["a.b.c"]) is True
        assert dotexists(data, ["x.y.z"], ["p.q.r"]) is False

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
        result = dget(data, None, default="default")
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
        assert Registry.get("test_func")() == "test_result"

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
        assert Registry.get("my_function")() == "result"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key raises ValueError."""
        with pytest.raises(ValueError, match="preprocessor nonexistent is not registered"):
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
        instance = Registry.get("test_class")()
        assert instance.method() == "class_result"


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
