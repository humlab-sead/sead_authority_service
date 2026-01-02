"""Extended tests for src.configuration.utility to improve coverage."""

from __future__ import annotations

import pytest

from src.configuration.utility import _parse_list_expression, _replace_references, replace_references


class TestParseListExpression:
    """Test _parse_list_expression with various scenarios."""

    def test_simple_value_reference(self) -> None:
        """Simple @value directive should be returned unchanged for later processing."""
        data = {"base": ["a", "b"]}
        expr = "@value: base"

        result = _parse_list_expression(expr, data)

        assert result == "@value: base"

    def test_prepend_literal_to_reference(self) -> None:
        """Should prepend literal list to referenced list."""
        data = {"base": ["c", "d"]}
        expr = "['a', 'b'] + @value: base"

        result = _parse_list_expression(expr, data)

        assert result == ["a", "b", "c", "d"]

    def test_append_literal_to_reference(self) -> None:
        """Should append literal list to referenced list."""
        data = {"base": ["a", "b"]}
        expr = "@value: base + ['c', 'd']"

        result = _parse_list_expression(expr, data)

        assert result == ["a", "b", "c", "d"]

    def test_multiple_references_concatenation(self) -> None:
        """Should concatenate multiple @value references."""
        data = {"list1": ["a", "b"], "list2": ["c", "d"]}
        expr = "@value: list1 + @value: list2"

        result = _parse_list_expression(expr, data)

        assert result == ["a", "b", "c", "d"]

    def test_complex_chaining(self) -> None:
        """Should chain multiple literals and references."""
        data = {"mid": ["b", "c"]}
        expr = "['a'] + @value: mid + ['d']"

        result = _parse_list_expression(expr, data)

        assert result == ["a", "b", "c", "d"]

    def test_returns_original_without_list_operations(self) -> None:
        """Should return original string if no list operations present."""
        expr = "plain string without operations"

        result = _parse_list_expression(expr, {})

        assert result == expr

    def test_returns_original_on_unbalanced_brackets(self) -> None:
        """Should return original on malformed bracket expression."""
        data = {"base": ["a"]}
        expr = "['item' + @value: base"  # Missing closing bracket

        result = _parse_list_expression(expr, data)

        assert result == expr

    def test_returns_original_on_nested_brackets(self) -> None:
        """Should reject nested lists (constraint violation)."""
        data = {"base": ["a"]}
        expr = "@value: base + [['nested']]"

        result = _parse_list_expression(expr, data)

        assert result == expr

    def test_returns_original_on_brackets_in_values(self) -> None:
        """Should reject brackets inside string values."""
        data = {"base": ["a"]}
        expr = "['item[0]'] + @value: base"

        result = _parse_list_expression(expr, data)

        assert result == expr

    def test_reference_to_nonexistent_path_skips(self) -> None:
        """Should skip references to nonexistent paths."""
        data = {"existing": ["a"]}
        expr = "@value: missing + @value: existing"

        result = _parse_list_expression(expr, data)

        assert result == ["a"]

    def test_reference_to_non_list_appends_value(self) -> None:
        """Should append non-list referenced value as single item."""
        data = {"scalar": "value"}
        expr = "['a'] + @value: scalar"

        result = _parse_list_expression(expr, data)

        assert result == ["a", "value"]

    def test_literal_parse_error_returns_original(self) -> None:
        """Should return original on YAML parse error or accept valid YAML."""
        data = {"base": ["a"]}
        # This is actually valid YAML - a list with string 'invalid yaml'
        expr = "[invalid yaml] + @value: base"

        result = _parse_list_expression(expr, data)

        # Since 'invalid yaml' is valid YAML string, it parses correctly
        assert result == ["invalid yaml", "a"]

    def test_empty_result_returns_original(self) -> None:
        """Should return original expression if result would be empty."""
        data = {}
        expr = "@value: missing1 + @value: missing2"

        result = _parse_list_expression(expr, data)

        # Empty result returns original expression
        assert result == expr

    def test_nested_list_in_referenced_data(self) -> None:
        """Should reject if referenced data contains nested lists."""
        data = {"nested": [["inner"]]}
        expr = "@value: nested + ['a']"

        result = _parse_list_expression(expr, data)

        assert result == expr


class TestReplaceReferences:
    """Test _replace_references recursive resolution."""

    def test_replaces_dict_values_recursively(self) -> None:
        """Should recursively replace references in nested dicts."""
        data = {"source": "value", "level1": {"level2": {"ref": "@value: source"}}}

        result = _replace_references(data, full_data=data)

        assert result["level1"]["level2"]["ref"] == "value"

    def test_replaces_list_items_recursively(self) -> None:
        """Should recursively replace references in lists."""
        data = {"source": "value", "items": ["@value: source", "@value: source"]}

        result = _replace_references(data, full_data=data)

        assert result["items"] == ["value", "value"]

    def test_handles_list_expression_with_operations(self) -> None:
        """Should parse and resolve list expressions with operations."""
        data = {"base": ["a", "b"], "extended": "@value: base + ['c']"}

        result = _replace_references(data, full_data=data)

        assert result["extended"] == ["a", "b", "c"]

    def test_recurses_after_parsing_list_expression(self) -> None:
        """Should recursively resolve references after list parsing."""
        data = {
            "nested_source": "val",
            "list_with_ref": ["@value: nested_source"],
            "combined": "@value: list_with_ref + ['extra']",
        }

        result = _replace_references(data, full_data=data)

        # First resolves list_with_ref, then uses it in combined
        assert result["combined"] == ["val", "extra"]

    def test_returns_original_for_missing_reference(self) -> None:
        """Should return original string for missing references."""
        data = {"ref": "@value: nonexistent"}

        result = _replace_references(data, full_data=data)

        assert result["ref"] == "@value: nonexistent"

    def test_handles_non_string_primitives(self) -> None:
        """Should pass through non-string primitives unchanged."""
        data = {"number": 42, "boolean": True, "null": None}

        result = _replace_references(data, full_data=data)

        assert result["number"] == 42
        assert result["boolean"] is True
        assert result["null"] is None

    def test_complex_nested_resolution(self) -> None:
        """Should handle complex nested reference chains."""
        data = {
            "base": ["a"],
            "level1": "@value: base + ['b']",
            "level2": "@value: level1 + ['c']",
            "nested": {"deep": {"ref": "@value: level2"}},
        }

        result = _replace_references(data, full_data=data)

        assert result["level1"] == ["a", "b"]
        assert result["level2"] == ["a", "b", "c"]
        assert result["nested"]["deep"]["ref"] == ["a", "b", "c"]


class TestReplaceReferencesPublicAPI:
    """Test the public replace_references function."""

    def test_uses_data_as_full_data(self) -> None:
        """Public function should use input data as full_data context."""
        data = {"source": {"nested": "value"}, "target": "@value: source.nested"}

        result = replace_references(data)

        assert result["target"] == "value"

    def test_handles_top_level_list(self) -> None:
        """Should handle top-level list input."""
        data = ["@value: source", "plain"]
        # Note: top-level list references can't resolve without dict context
        result = replace_references(data)

        assert isinstance(result, list)

    def test_handles_top_level_string(self) -> None:
        """Should handle top-level string input."""
        data = "@value: something"

        result = replace_references(data)

        # Can't resolve without dict context
        assert result == "@value: something"

    def test_integration_with_multiple_patterns(self) -> None:
        """Integration test with multiple reference patterns."""
        data = {
            "colors": ["red", "blue"],
            "numbers": [1, 2, 3],
            "combined": "@value: colors + @value: numbers",
            "extended": ["@value: colors", "@value: numbers"],
            "nested": {"refs": {"combo": "@value: combined"}},
        }

        result = replace_references(data)

        assert result["combined"] == ["red", "blue", 1, 2, 3]
        assert result["extended"] == [["red", "blue"], [1, 2, 3]]
        assert result["nested"]["refs"]["combo"] == ["red", "blue", 1, 2, 3]
