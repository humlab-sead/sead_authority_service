"""Unit tests for arbodat utility functions."""

import pandas as pd
import pytest

from src.arbodat.utility import _rename_last_occurence, add_surrogate_id, check_functional_dependency, get_subset


class TestAddSurrogateId:
    """Tests for add_surrogate_id function."""

    def test_adds_surrogate_id_starting_at_1(self):
        """Test that surrogate ID starts at 1."""
        df = pd.DataFrame({"name": ["A", "B", "C"]})
        result = add_surrogate_id(df, "id")

        assert "id" in result.columns
        assert result["id"].tolist() == [1, 2, 3]

    def test_preserves_existing_data(self):
        """Test that existing data is preserved."""
        df = pd.DataFrame({"name": ["A", "B"], "value": [10, 20]})
        result = add_surrogate_id(df, "id")

        assert result["name"].tolist() == ["A", "B"]
        assert result["value"].tolist() == [10, 20]

    def test_resets_index(self):
        """Test that index is reset."""
        df = pd.DataFrame({"name": ["A", "B", "C"]}, index=[5, 10, 15])
        result = add_surrogate_id(df, "id")

        assert result["id"].tolist() == [1, 2, 3]
        assert result.index.tolist() == [0, 1, 2]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"name": []})
        result = add_surrogate_id(df, "id")

        assert len(result) == 0
        assert "id" in result.columns


class TestCheckFunctionalDependency:
    """Tests for check_functional_dependency function."""

    def test_valid_functional_dependency(self):
        """Test with valid functional dependency."""
        df = pd.DataFrame({"key": ["A", "A", "B", "B"], "value": [1, 1, 2, 2]})

        result = check_functional_dependency(df, ["key"], raise_error=False)
        assert result is True

    def test_invalid_functional_dependency_raises(self):
        """Test that invalid dependency raises error."""
        df = pd.DataFrame({"key": ["A", "A", "B"], "value": [1, 2, 3]})

        with pytest.raises(ValueError, match="inconsistent non-subset values"):
            check_functional_dependency(df, ["key"], raise_error=True)

    def test_invalid_functional_dependency_warns(self):
        """Test that invalid dependency warns when raise_error=False."""
        df = pd.DataFrame({"key": ["A", "A"], "value": [1, 2]})

        result = check_functional_dependency(df, ["key"], raise_error=False)
        assert result is False

    def test_no_dependent_columns(self):
        """Test with only determinant columns."""
        df = pd.DataFrame({"key": ["A", "B", "C"]})

        result = check_functional_dependency(df, ["key"], raise_error=True)
        assert result is True

    def test_multiple_determinant_columns(self):
        """Test with multiple determinant columns."""
        df = pd.DataFrame({"key1": ["A", "A", "B", "B"], "key2": [1, 2, 1, 2], "value": [10, 20, 30, 40]})

        result = check_functional_dependency(df, ["key1", "key2"], raise_error=False)
        assert result is True


class TestGetSubset:
    """Tests for get_subset function."""

    def test_basic_column_extraction(self):
        """Test extracting basic columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = get_subset(df, ["A", "B"])

        assert list(result.columns) == ["A", "B"]
        assert len(result) == 2

    def test_raises_on_none_source(self):
        """Test that None source raises ValueError."""
        with pytest.raises(ValueError, match="Source DataFrame must be provided"):
            get_subset(None, ["A"])  # type: ignore

    def test_missing_columns_raises_error(self):
        """Test that missing columns raise error by default."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        with pytest.raises(ValueError, match="Columns not found"):
            get_subset(df, ["A", "C"])

    def test_missing_columns_warns_when_not_raising(self):
        """Test that missing columns warn when raise_if_missing=False."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A", "C"], raise_if_missing=False)

        assert list(result.columns) == ["A"]
        assert len(result) == 2

    def test_extra_columns_rename_source_column(self):
        """Test renaming source column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"D": "C"})

        assert list(result.columns) == ["A", "D"]
        assert result["D"].tolist() == [5, 6]
        assert "C" not in result.columns

    def test_extra_columns_add_constant(self):
        """Test adding constant column via extra_columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"constant": "fixed_value"})

        assert "constant" in result.columns
        assert result["constant"].tolist() == ["fixed_value", "fixed_value"]

    def test_extra_columns_add_numeric_constant(self):
        """Test adding numeric constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"num": 42})

        assert result["num"].tolist() == [42, 42]

    def test_extra_columns_add_null_constant(self):
        """Test adding null constant column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"nullable": None})

        assert result["nullable"].isna().all()

    def test_extra_columns_mixed_rename_and_constant(self):
        """Test mixing column rename and constant addition."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        result = get_subset(df, ["A"], extra_columns={"renamed_B": "B", "constant": 100})

        assert list(result.columns) == ["A", "renamed_B", "constant"]
        assert result["renamed_B"].tolist() == [3, 4]
        assert result["constant"].tolist() == [100, 100]

    def test_extra_columns_nonexistent_source_as_constant(self):
        """Test that non-existent source column name is treated as constant."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"new_col": "NonExistent"})

        assert "new_col" in result.columns
        assert result["new_col"].tolist() == ["NonExistent", "NonExistent"]

    def test_drop_duplicates_true(self):
        """Test dropping all duplicates."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=True)

        assert len(result) == 2

    def test_drop_duplicates_by_subset(self):
        """Test dropping duplicates by subset of columns."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 4, 5]})

        result = get_subset(df, ["A", "B"], drop_duplicates=["A"])

        assert len(result) == 2
        assert result["A"].tolist() == [1, 2]

    def test_drop_duplicates_false(self):
        """Test keeping duplicates when drop_duplicates=False."""
        df = pd.DataFrame({"A": [1, 1, 2], "B": [3, 3, 4]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert len(result) == 3

    def test_functional_dependency_check_passes(self):
        """Test functional dependency check with valid data."""
        df = pd.DataFrame({"key": [1, 1, 2, 2], "value": [10, 10, 20, 20]})

        result = get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

        assert len(result) == 2

    def test_functional_dependency_check_fails(self):
        """Test functional dependency check with invalid data."""
        df = pd.DataFrame({"key": [1, 1, 2], "value": [10, 20, 30]})

        with pytest.raises(ValueError, match="inconsistent"):
            get_subset(df, ["key", "value"], drop_duplicates=["key"], fd_check=True)

    def test_add_surrogate_id_when_not_present(self):
        """Test adding surrogate ID when not in result."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A", "B"], surrogate_id="id")

        assert "id" in result.columns
        assert result["id"].tolist() == [1, 2]

    def test_dont_add_surrogate_id_when_present(self):
        """Test not adding surrogate ID when already present."""
        df = pd.DataFrame({"A": [1, 2], "id": [10, 20]})

        result = get_subset(df, ["A", "id"], surrogate_id="id")

        assert result["id"].tolist() == [10, 20]

    def test_surrogate_id_none_skips_addition(self):
        """Test that None surrogate_id skips ID addition."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A", "B"], surrogate_id=None)

        assert "id" not in result.columns
        assert len(result.columns) == 2

    def test_complex_workflow(self):
        """Test complex workflow with all features."""
        df = pd.DataFrame({"site_name": ["Site A", "Site A", "Site B"], "location": ["Loc1", "Loc1", "Loc2"], "value": [100, 100, 200]})

        result = get_subset(
            df,
            ["site_name", "location"],
            extra_columns={"renamed_val": "value", "type": "survey"},
            drop_duplicates=["site_name", "location"],
            surrogate_id="site_id",
        )

        assert len(result) == 2
        assert list(result.columns) == ["site_name", "location", "renamed_val", "type", "site_id"]
        assert result["renamed_val"].tolist() == [100, 200]
        assert result["type"].tolist() == ["survey", "survey"]
        assert result["site_id"].tolist() == [1, 2]

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"A": [], "B": []})

        result = get_subset(df, ["A"], extra_columns={"C": 1}, surrogate_id="id")

        assert len(result) == 0
        assert "A" in result.columns
        assert "C" in result.columns
        assert "id" in result.columns

    def test_single_row(self):
        """Test with single row DataFrame."""
        df = pd.DataFrame({"A": [1], "B": [2]})

        result = get_subset(df, ["A"], extra_columns={"renamed": "B"})

        assert len(result) == 1
        assert result["renamed"].tolist() == [2]

    def test_preserves_data_types(self):
        """Test that data types are preserved."""
        df = pd.DataFrame({"int_col": [1, 2], "float_col": [1.5, 2.5], "str_col": ["a", "b"]})

        result = get_subset(df, ["int_col", "float_col", "str_col"])

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype

    def test_column_order_preserved(self):
        """Test that column order matches specification."""
        df = pd.DataFrame({"C": [1, 2], "B": [3, 4], "A": [5, 6]})

        result = get_subset(df, ["A", "B", "C"])

        # Order should be A, B, C as requested (not source order)
        assert list(result.columns) == ["A", "B", "C"]

    def test_extra_columns_empty_dict(self):
        """Test that empty extra_columns dict works."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={})

        assert list(result.columns) == ["A"]

    def test_rename_to_same_name(self):
        """Test renaming column to itself (no-op)."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = get_subset(df, ["A"], extra_columns={"B": "B"})

        assert list(result.columns) == ["A", "B"]
        assert result["B"].tolist() == [3, 4]

    def test_boolean_column_values(self):
        """Test with boolean column values."""
        df = pd.DataFrame({"A": [True, False, True], "B": [1, 2, 3]})

        result = get_subset(df, ["A", "B"], drop_duplicates=False)

        assert result["A"].tolist() == [True, False, True]

    def test_with_null_values(self):
        """Test handling of null values."""
        df = pd.DataFrame({"A": [1, None, 3], "B": [4, 5, None]})

        result = get_subset(df, ["A", "B"])

        assert pd.isna(result.iloc[1]["A"])
        assert pd.isna(result.iloc[2]["B"])


class TestRenameLastOccurrence:
    """Test suite for _rename_last_occurence helper function."""

    def test_basic_rename_single_occurrence(self):
        """Test renaming a column that appears once."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = _rename_last_occurence(data, {"B": "B_renamed"})
        expected = ["A", "B_renamed", "C"]
        assert result == expected

    def test_rename_last_when_multiple_occurrences(self):
        """Test that only the LAST occurrence is renamed when column appears multiple times."""
        # Create DataFrame with duplicate column names
        data = pd.DataFrame([[1, 2, 3, 4]], columns=["A", "B", "A", "C"])
        result = _rename_last_occurence(data, {"A": "A_last"})
        expected = ["A", "B", "A_last", "C"]
        assert result == expected

    def test_skip_when_source_not_in_columns(self):
        """Test that rename is skipped when source column doesn't exist."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = _rename_last_occurence(data, {"C": "C_renamed"})
        expected = ["A", "B"]
        assert result == expected

    def test_skip_when_target_already_exists(self):
        """Test that rename is skipped when target name already exists in columns."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = _rename_last_occurence(data, {"A": "C"})
        expected = ["A", "B", "C"]
        assert result == expected

    def test_multiple_renames_in_single_call(self):
        """Test renaming multiple columns in a single call."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6], "D": [7, 8]})
        result = _rename_last_occurence(data, {"A": "A_new", "C": "C_new"})
        expected = ["A_new", "B", "C_new", "D"]
        assert result == expected

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        data = pd.DataFrame()
        result = _rename_last_occurence(data, {"A": "A_renamed"})
        expected = []
        assert result == expected

    def test_empty_rename_map(self):
        """Test with empty rename map."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = _rename_last_occurence(data, {})
        expected = ["A", "B"]
        assert result == expected

    def test_rename_with_duplicate_occurrences_multiple_sources(self):
        """Test renaming when multiple columns have duplicates."""
        # DataFrame with multiple duplicate columns
        data = pd.DataFrame([[1, 2, 3, 4, 5, 6]], columns=["A", "B", "A", "C", "B", "D"])
        result = _rename_last_occurence(data, {"A": "A_last", "B": "B_last"})
        expected = ["A", "B", "A_last", "C", "B_last", "D"]
        assert result == expected

    def test_rename_does_not_modify_dataframe(self):
        """Test that the original DataFrame columns are not modified."""
        data = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        original_columns = data.columns.tolist()
        _rename_last_occurence(data, {"B": "B_renamed"})
        assert data.columns.tolist() == original_columns

    def test_rename_first_occurrence_not_affected(self):
        """Test that earlier occurrences of duplicate columns remain unchanged."""
        data = pd.DataFrame([[1, 2, 3, 4, 5]], columns=["A", "B", "A", "A", "C"])
        result = _rename_last_occurence(data, {"A": "A_final"})
        expected = ["A", "B", "A", "A_final", "C"]
        assert result == expected

    def test_rename_with_special_characters_in_names(self):
        """Test renaming columns with special characters."""
        data = pd.DataFrame({"col.1": [1, 2], "col-2": [3, 4], "col_3": [5, 6]})
        result = _rename_last_occurence(data, {"col.1": "column_1", "col-2": "column-2"})
        expected = ["column_1", "column-2", "col_3"]
        assert result == expected
