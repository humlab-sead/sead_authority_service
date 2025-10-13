"""
Unit tests for LLM input formatting functionality.
"""

import json
from unittest.mock import patch

import pytest

from src.strategies.llm.input_format import (  # create_blurb_for_records,
    CSVFormatter,
    FormatterRegistry,
    Formatters,
    JSONFormatter,
    MarkdownFormatter,
    _has_non_scalar,
    _is_scalar,
    _resolve_format,
    _total_chars,
    format_rows_for_llm,
)


class TestFormatterRegistry:
    """Test the formatter registry system"""

    def test_registry_inheritance(self):
        """Test that FormatterRegistry inherits from Registry"""
        assert hasattr(FormatterRegistry, "items")
        assert isinstance(Formatters, FormatterRegistry)

    def test_formatters_registered(self):
        """Test that formatters are properly registered"""
        # Note: There's a duplicate registration issue in the original code
        # Both CSVFormatter and JSONFormatter are registered as "csv"
        assert "markdown" in Formatters.items
        assert "csv" in Formatters.items

    def test_get_formatter(self):
        """Test getting formatters from registry"""
        markdown_formatter = Formatters.get("markdown")
        assert issubclass(markdown_formatter, MarkdownFormatter)

        with pytest.raises(KeyError):
            Formatters.get("whatnot")


class TestMarkdownFormatter:
    """Test MarkdownFormatter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.formatter = MarkdownFormatter()  # pylint: disable=attribute-defined-outside-init

    def test_empty_columns(self):
        """Test formatting with empty columns"""
        result = self.formatter.format([], columns=[])
        assert result == "_(no rows)_"

    def test_single_row(self):
        """Test formatting a single row"""
        rows = [{"name": "John", "age": 30}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        expected = "| name | age |\n| --- | --- |\n| John | 30 |"
        assert result == expected

    def test_multiple_rows(self):
        """Test formatting multiple rows"""
        rows = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        lines = result.split("\n")
        assert len(lines) == 4
        assert "| name | age |" in lines[0]
        assert "| --- | --- |" in lines[1]
        assert "| John | 30 |" in lines[2]
        assert "| Jane | 25 |" in lines[3]

    def test_escaping_pipes(self):
        """Test that pipes are properly escaped"""
        rows = [{"data": "value|with|pipes"}]
        columns = ["data"]
        result = self.formatter.format(rows, columns=columns)

        assert r"value\|with\|pipes" in result

    def test_escaping_newlines(self):
        """Test that newlines are properly escaped"""
        rows = [{"data": "line1\nline2"}]
        columns = ["data"]
        result = self.formatter.format(rows, columns=columns)

        assert "line1↩line2" in result

    def test_none_values(self):
        """Test handling of None values"""
        rows = [{"name": "John", "age": None}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        assert "| John |  |" in result

    def test_missing_columns(self):
        """Test handling of missing columns in rows"""
        rows = [{"name": "John"}]  # Missing age column
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        assert "| John |  |" in result

    def test_empty_rows_with_columns(self):
        """Test formatting with columns but no rows"""
        result = self.formatter.format([], columns=["name", "age"])

        expected = "| name | age |\n| --- | --- |"
        assert result == expected


class TestCSVFormatter:
    """Test CSVFormatter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.formatter = CSVFormatter()  # pylint: disable=attribute-defined-outside-init

    def test_empty_columns(self):
        """Test formatting with empty columns"""
        result = self.formatter.format([], columns=[])
        assert result == ""

    def test_single_row(self):
        """Test formatting a single row"""
        rows = [{"name": "John", "age": 30}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "name|age" == lines[0]
        assert "John|30" == lines[1]

    def test_custom_separator(self):
        """Test formatting with custom separator"""
        rows = [{"name": "John", "age": 30}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns, sep=",")

        lines = result.strip().split("\n")
        assert "name,age" == lines[0]
        assert "John,30" == lines[1]

    def test_quoting_needed(self):
        """Test CSV quoting when needed"""
        rows = [{"data": "value,with,commas"}]
        columns = ["data"]
        result = self.formatter.format(rows, columns=columns, sep=",")

        assert '"value,with,commas"' in result

    def test_none_values(self):
        """Test handling of None values"""
        rows = [{"name": "John", "age": None}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        lines = result.strip().split("\n")
        assert "John|" == lines[1]

    def test_missing_columns(self):
        """Test handling of missing columns"""
        rows = [{"name": "John"}]  # Missing age
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        lines = result.strip().split("\n")
        assert "John|" == lines[1]

    def test_multiple_rows(self):
        """Test formatting multiple rows"""
        rows = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "name|age" == lines[0]
        assert "John|30" == lines[1]
        assert "Jane|25" == lines[2]


class TestJSONFormatter:
    """Test JSONFormatter functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.formatter = JSONFormatter()  # pylint: disable=attribute-defined-outside-init

    def test_empty_rows(self):
        """Test formatting empty rows"""
        result = self.formatter.format([], ["name", "age"])
        assert result == "[]"

    def test_single_row(self):
        """Test formatting a single row"""
        rows = [{"name": "John", "age": 30}]
        columns = ["name", "age"]  # columns parameter is ignored in JSON formatter
        result = self.formatter.format(rows, columns=columns)

        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "John"
        assert parsed[0]["age"] == 30

    def test_multiple_rows(self):
        """Test formatting multiple rows"""
        rows = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        columns = ["name", "age"]
        result = self.formatter.format(rows, columns=columns)

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "John"
        assert parsed[1]["name"] == "Jane"

    def test_complex_data(self):
        """Test formatting with complex data structures"""
        rows = [{"data": {"nested": "value"}, "list": [1, 2, 3]}]
        columns = ["data", "list"]
        result = self.formatter.format(rows, columns=columns)

        parsed = json.loads(result)
        assert parsed[0]["data"]["nested"] == "value"
        assert parsed[0]["list"] == [1, 2, 3]

    def test_unicode_handling(self):
        """Test handling of Unicode characters"""
        rows = [{"name": "Björk", "city": "Reykjavík"}]
        columns = ["name", "city"]
        result = self.formatter.format(rows, columns=columns)

        # Should not escape Unicode characters
        assert "Björk" in result
        assert "Reykjavík" in result

    def test_columns_parameter_ignored(self):
        """Test that columns parameter is ignored"""
        rows = [{"name": "John", "age": 30, "city": "NYC"}]
        columns = ["name"]  # Only specify name, but all fields should be included
        result = self.formatter.format(rows, columns=columns)

        parsed = json.loads(result)
        assert "name" in parsed[0]
        assert "age" in parsed[0]
        assert "city" in parsed[0]


class TestUtilityFunctions:
    """Test utility functions"""

    def test_is_scalar_true_cases(self):
        """Test _is_scalar returns True for scalar types"""
        assert _is_scalar("string")
        assert _is_scalar(42)
        assert _is_scalar(3.14)
        assert _is_scalar(True)
        assert _is_scalar(False)
        assert _is_scalar(None)

    def test_is_scalar_false_cases(self):
        """Test _is_scalar returns False for non-scalar types"""
        assert not _is_scalar([1, 2, 3])
        assert not _is_scalar({"key": "value"})
        assert not _is_scalar(set())
        assert not _is_scalar(tuple())

    def test_has_non_scalar_true(self):
        """Test _has_non_scalar returns True when non-scalar values present"""
        rows = [{"name": "John", "data": [1, 2, 3]}, {"name": "Jane", "age": 25}]
        assert _has_non_scalar(rows)

    def test_has_non_scalar_false(self):
        """Test _has_non_scalar returns False when only scalars present"""
        rows = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
        assert not _has_non_scalar(rows)

    def test_has_non_scalar_empty(self):
        """Test _has_non_scalar with empty rows"""
        assert not _has_non_scalar([])

    def test_total_chars(self):
        """Test _total_chars calculation"""
        rows = [{"name": "John", "age": 30}, {"name": "Jane", "age": None}]  # 4 + 2 = 6 chars  # 4 + 4 (None) = 8 chars
        result = _total_chars(rows)
        assert result == 14  # 6 + 8

    def test_total_chars_empty(self):
        """Test _total_chars with empty rows"""
        assert _total_chars([]) == 0

    def test_resolve_format_auto_markdown(self):
        """Test _resolve_format chooses markdown for small data"""
        result = _resolve_format("auto", n_rows=10, has_non_scalar=False, total_chars=1000)
        assert result == "markdown"

    def test_resolve_format_auto_csv(self):
        """Test _resolve_format chooses CSV for medium data"""
        result = _resolve_format("auto", n_rows=100, has_non_scalar=False, total_chars=30000)
        assert result == "csv"

    def test_resolve_format_auto_json_large_rows(self):
        """Test _resolve_format chooses JSON for large row count"""
        result = _resolve_format("auto", n_rows=300, has_non_scalar=False, total_chars=1000)
        assert result == "json"

    def test_resolve_format_auto_json_non_scalar(self):
        """Test _resolve_format chooses JSON for non-scalar data"""
        result = _resolve_format("auto", n_rows=10, has_non_scalar=True, total_chars=1000)
        assert result == "json"

    def test_resolve_format_explicit(self):
        """Test _resolve_format respects explicit format"""
        assert _resolve_format("markdown", 1000, True, 50000) == "markdown"
        assert _resolve_format("csv", 1000, True, 50000) == "csv"
        assert _resolve_format("json", 10, False, 100) == "json"


# class TestCreateBlurbForRecords:
#     """Test blurb creation functionality"""

#     def test_basic_blurb(self):
#         """Test basic blurb creation"""
#         rows = [{"id": "1", "label": "Test"}]
#         columns = ["id", "label"]
#         blurb = create_blurb_for_records(rows, "test entity", columns, "markdown")

#         assert "1 test entity candidate records" in blurb
#         assert "MARKDOWN format" in blurb
#         assert "Columns: id, label" in blurb
#         assert "Return the `id`" in blurb

#     def test_blurb_with_description(self):
#         """Test blurb creation with description column"""
#         rows = [{"id": "1", "label": "Test", "description": "A test item"}]
#         columns = ["id", "label", "description"]
#         blurb = create_blurb_for_records(rows, "sample", columns, "csv")

#         assert "Use `label` for name matching and `description` for context" in blurb
#         assert "CSV format" in blurb

#     def test_blurb_no_label_column(self):
#         """Test blurb creation without label column"""
#         rows = [{"id": "1", "name": "Test"}]
#         columns = ["id", "name"]
#         blurb = create_blurb_for_records(rows, "item", columns, "json")

#         assert "Use `label` for name matching" not in blurb
#         assert "JSON format" in blurb

#     def test_blurb_empty_rows(self):
#         """Test blurb creation with empty rows"""
#         blurb = create_blurb_for_records([], "entity", ["id"], "markdown")

#         assert "0 entity candidate records" in blurb

#     def test_blurb_no_columns(self):
#         """Test blurb creation with no columns"""
#         with pytest.raises(ValueError):
#             create_blurb_for_records([{}], "entity", [], "markdown")


class TestFormatRowsForLLM:
    """Test main formatting function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sample_rows = [  # pylint: disable=attribute-defined-outside-init
            {"id": "1", "label": "Uppsala", "description": "City in Sweden"},
            {"id": "2", "label": "Stockholm", "description": "Capital of Sweden"},
        ]

    def test_basic_formatting(self):
        """Test basic formatting functionality"""
        table_format, table = format_rows_for_llm(self.sample_rows, target_format="markdown")

        assert isinstance(table, str)
        assert isinstance(table_format, str)
        assert "Uppsala" in table
        assert "Stockholm" in table
        assert table_format == "markdown"

    def test_custom_column_map(self):
        """Test formatting with custom column mapping"""
        rows = [{"biblio_id": "123", "title": "Test Article", "authors": "Smith, J."}]
        column_map = {"id": "biblio_id", "label": "title", "description": "authors"}

        table_format, table = format_rows_for_llm(rows, column_map=column_map, target_format="markdown")

        assert "Test Article" in table
        assert "Smith, J." in table
        assert table_format == "markdown"

    def test_auto_format_selection(self):
        """Test automatic format selection"""
        # Small data should use markdown
        _, table = format_rows_for_llm(self.sample_rows[:1], target_format="auto")

        # Should contain markdown table indicators
        assert "|" in table and "---" in table

    def test_csv_format(self):
        """Test CSV formatting"""
        table_format, table = format_rows_for_llm(self.sample_rows, target_format="csv", sep=",")

        lines = table.strip().split("\n")
        assert "id,label,description" in lines[0]
        assert table_format == "csv"

    def test_json_format(self):
        """Test JSON formatting"""
        table_format, table = format_rows_for_llm(self.sample_rows, target_format="json")

        parsed = json.loads(table)
        assert len(parsed) == 2
        assert parsed[0]["label"] == "Uppsala"
        assert table_format == "json"

    def test_minimal_column_map(self):
        """Test with minimal column map (id and label only)"""
        rows = [{"user_id": "123", "username": "johndoe"}]
        column_map = {"id": "user_id", "label": "username"}

        _, table = format_rows_for_llm(rows, column_map=column_map, target_format="markdown")

        assert "johndoe" in table

    def test_invalid_column_map_keys(self):
        """Test error handling for invalid column map keys"""
        with pytest.raises(KeyError, match="Map keys must all be from"):
            format_rows_for_llm(self.sample_rows, column_map={"invalid_key": "some_field"})

    def test_missing_columns_in_rows(self):
        """Test handling of missing columns in data rows"""
        rows = [{"id": "1", "name": "Test"}]  # Missing 'label' field

        # Should not raise error, should handle gracefully
        table_format, table = format_rows_for_llm(rows, target_format="markdown")

        assert isinstance(table, str)
        assert isinstance(table_format, str)

    def test_large_dataset_auto_format(self):
        """Test auto format selection for large datasets"""
        # Create large dataset that should trigger JSON format
        large_rows = [{"id": str(i), "label": f"Item {i}"} for i in range(300)]

        with patch("src.strategies.llm.input_format._resolve_format") as mock_resolve:
            mock_resolve.return_value = "json"

            table_format, table = format_rows_for_llm(large_rows, target_format="auto")

            mock_resolve.assert_called_once()
            assert table.startswith("[") and table.endswith("]")  # Should be JSON array
            assert table_format == "json"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_rows(self):
        """Test formatting empty row list"""
        _, table = format_rows_for_llm([], target_format="markdown")

        assert "No records available." in table

    def test_rows_with_complex_data(self):
        """Test rows containing complex data structures"""
        rows = [{"id": "1", "label": {"nested": "value"}, "description": []}]

        # Should automatically choose JSON format
        _, table = format_rows_for_llm(rows, target_format="auto")

        # Should be valid JSON
        parsed = json.loads(table)
        assert parsed[0]["label"]["nested"] == "value"

    def test_unicode_data(self):
        """Test handling of Unicode characters"""
        rows = [{"id": "1", "label": "Åpfel", "description": "Français"}]

        _, table = format_rows_for_llm(rows, target_format="markdown")

        assert "Åpfel" in table
        assert "Français" in table

    @patch("src.strategies.llm.input_format.Formatters.get")
    def test_formatter_registry_error(self, mock_get):
        """Test error handling when formatter is not found"""
        mock_get.side_effect = KeyError("formatter not found")

        with pytest.raises(KeyError):
            format_rows_for_llm([{"id": "1", "label": "test"}], target_format="nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
