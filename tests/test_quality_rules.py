"""Tests for quality validation rules."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from depivot.quality_rules import (
    CheckNullValues,
    CheckDuplicates,
    CheckColumnTypes,
    CheckValueRanges,
    CheckRequiredColumns,
    CheckRowCount,
    CheckNumericConversion,
    CheckOutliers,
    CheckDataCompleteness,
    CheckTotalsMatch,
    RULE_REGISTRY,
)
from depivot.data_quality import ValidationContext


# =============================================================================
# PRE-PROCESSING RULES TESTS
# =============================================================================

class TestCheckNullValues:
    """Test null value checking rule."""

    def test_check_null_values_pass(self):
        """Test passing validation with low null ratio."""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": [10, 20, 30, 40, 50],
        })
        context = ValidationContext(df=df)
        rule = CheckNullValues({
            "enabled": True,
            "severity": "error",
            "message": "Excessive NULLs in {column}: {percent}% (threshold: {threshold}%)",
            "params": {"columns": "all", "threshold": 0.05}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert result.severity == "error"
        assert "No excessive NULL values" in result.message

    def test_check_null_values_fail(self):
        """Test failing validation with high null ratio."""
        df = pd.DataFrame({
            "A": [1, None, None, None, None],
            "B": [10, 20, 30, 40, 50],
        })
        context = ValidationContext(df=df)
        rule = CheckNullValues({
            "enabled": True,
            "severity": "warning",
            "message": "Excessive NULLs in {column}: {percent}% (threshold: {threshold}%)",
            "params": {"columns": ["A"], "threshold": 0.5}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.severity == "warning"
        assert "Excessive NULLs" in result.message
        assert result.details["total_issues"] == 1
        assert result.details["issues"][0]["column"] == "A"
        assert result.details["issues"][0]["null_ratio"] == 0.8

    def test_check_null_values_specific_columns(self):
        """Test checking specific columns only."""
        df = pd.DataFrame({
            "A": [1, None, None, 4, 5],
            "B": [None, None, None, None, None],
            "C": [100, 200, 300, 400, 500],
        })
        context = ValidationContext(df=df)
        rule = CheckNullValues({
            "enabled": True,
            "severity": "error",
            "message": "Excessive NULLs in {column}",
            "params": {"columns": ["A", "C"], "threshold": 0.3}  # Only check A and C
        })

        result = rule.validate(context)

        assert result.passed is False
        # Should only flag A (0.4 ratio), not B (not checked) or C (0.0 ratio)
        assert result.details["total_issues"] == 1
        assert result.details["issues"][0]["column"] == "A"

    def test_check_null_values_per_column(self):
        """Test per-column null value checking."""
        df = pd.DataFrame({
            "A": [1, None, 3],
            "B": [None, None, 3],
        })
        context = ValidationContext(df=df)
        rule = CheckNullValues({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"columns": "all", "threshold": 0.5, "per_column": True}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["total_issues"] == 1  # Only B exceeds threshold

    def test_check_null_values_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame({"A": [], "B": []})
        context = ValidationContext(df=df)
        rule = CheckNullValues({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"columns": "all", "threshold": 0.05}
        })

        result = rule.validate(context)

        assert result.passed is True


class TestCheckDuplicates:
    """Test duplicate checking rule."""

    def test_check_duplicates_no_duplicates(self):
        """Test with no duplicate rows."""
        df = pd.DataFrame({
            "A": [1, 2, 3],
            "B": [10, 20, 30],
        })
        context = ValidationContext(df=df)
        rule = CheckDuplicates({
            "enabled": True,
            "severity": "error",
            "message": "Found {count} duplicates",
            "params": {}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert "No duplicates detected" in result.message

    def test_check_duplicates_full_row(self):
        """Test full row duplicate detection."""
        df = pd.DataFrame({
            "A": [1, 2, 1],
            "B": [10, 20, 10],
        })
        context = ValidationContext(df=df)
        rule = CheckDuplicates({
            "enabled": True,
            "severity": "warning",
            "message": "Found {count} duplicates",
            "params": {}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["duplicate_count"] == 2  # Rows 0 and 2
        assert "Found 2 duplicates" in result.message

    def test_check_duplicates_key_columns(self):
        """Test duplicate detection on specific key columns."""
        df = pd.DataFrame({
            "ID": [1, 2, 1],
            "Name": ["Alice", "Bob", "Charlie"],
            "Value": [100, 200, 300],
        })
        context = ValidationContext(df=df)
        rule = CheckDuplicates({
            "enabled": True,
            "severity": "error",
            "message": "Found {count} duplicates",
            "params": {"key_columns": ["ID"]}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["duplicate_count"] == 2  # Rows with ID=1
        assert result.details["key_columns"] == ["ID"]

    def test_check_duplicates_sample_limit(self):
        """Test that sample duplicates are limited."""
        df = pd.DataFrame({
            "A": [1] * 10,  # 10 duplicate rows
            "B": [2] * 10,
        })
        context = ValidationContext(df=df)
        rule = CheckDuplicates({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["duplicate_count"] == 10
        assert len(result.details["sample_duplicates"]) == 5  # Limited to 5


class TestCheckColumnTypes:
    """Test column type validation rule."""

    def test_check_column_types_match(self):
        """Test when all column types match."""
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "Name": ["Alice", "Bob", "Charlie"],
            "Amount": [100.5, 200.3, 300.7],
        })
        context = ValidationContext(df=df)
        rule = CheckColumnTypes({
            "enabled": True,
            "severity": "error",
            "message": "Type mismatch in {column}: expected {expected}, got {actual}",
            "params": {
                "type_specs": {
                    "ID": "numeric",
                    "Name": "string",
                    "Amount": "numeric",
                }
            }
        })

        result = rule.validate(context)

        assert result.passed is True
        assert "All column types match" in result.message

    def test_check_column_types_mismatch(self):
        """Test when column types don't match."""
        df = pd.DataFrame({
            "ID": ["A", "B", "C"],  # String instead of numeric
            "Amount": [100, 200, 300],
        })
        context = ValidationContext(df=df)
        rule = CheckColumnTypes({
            "enabled": True,
            "severity": "error",
            "message": "Type mismatch in {column}: expected {expected}, got {actual}",
            "params": {
                "type_specs": {
                    "ID": "numeric",
                    "Amount": "numeric",
                }
            }
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["total_issues"] == 1
        assert result.details["issues"][0]["column"] == "ID"
        assert result.details["issues"][0]["expected"] == "numeric"
        assert result.details["issues"][0]["actual"] == "string"

    def test_check_column_types_missing_column(self):
        """Test when expected column is missing."""
        df = pd.DataFrame({"A": [1, 2, 3]})
        context = ValidationContext(df=df)
        rule = CheckColumnTypes({
            "enabled": True,
            "severity": "error",
            "message": "Type mismatch in {column}: expected {expected}, got {actual}",
            "params": {"type_specs": {"B": "numeric"}}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["issues"][0]["column"] == "B"
        assert result.details["issues"][0]["issue"] == "missing"

    def test_check_column_types_datetime(self):
        """Test datetime type detection."""
        df = pd.DataFrame({
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        })
        context = ValidationContext(df=df)
        rule = CheckColumnTypes({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"type_specs": {"Date": "datetime"}}
        })

        result = rule.validate(context)

        assert result.passed is True


class TestCheckValueRanges:
    """Test value range validation rule."""

    def test_check_value_ranges_within(self):
        """Test when all values are within range."""
        df = pd.DataFrame({"Amount": [10, 20, 30, 40, 50]})
        context = ValidationContext(df=df)
        rule = CheckValueRanges({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"ranges": {"Amount": {"min": 0, "max": 100}}}
        })

        result = rule.validate(context)

        assert result.passed is True

    def test_check_value_ranges_outliers(self):
        """Test when values are outside range."""
        df = pd.DataFrame({"Amount": [-10, 20, 30, 120]})
        context = ValidationContext(df=df)
        rule = CheckValueRanges({
            "enabled": True,
            "severity": "warning",
            "message": "{count} outliers in {column}",
            "params": {"ranges": {"Amount": {"min": 0, "max": 100}}}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["issues"][0]["outlier_count"] == 2  # -10 and 120
        assert result.details["issues"][0]["column"] == "Amount"

    def test_check_value_ranges_only_min(self):
        """Test with only minimum value specified."""
        df = pd.DataFrame({"Value": [5, 10, 15]})
        context = ValidationContext(df=df)
        rule = CheckValueRanges({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"ranges": {"Value": {"min": 8}}}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["issues"][0]["outlier_count"] == 1  # 5 is below min

    def test_check_value_ranges_only_max(self):
        """Test with only maximum value specified."""
        df = pd.DataFrame({"Value": [5, 10, 15]})
        context = ValidationContext(df=df)
        rule = CheckValueRanges({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"ranges": {"Value": {"max": 12}}}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["issues"][0]["outlier_count"] == 1  # 15 is above max


class TestCheckRequiredColumns:
    """Test required columns validation rule."""

    def test_check_required_columns_present(self):
        """Test when all required columns are present."""
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "Name": ["A", "B", "C"],
            "Value": [10, 20, 30],
        })
        context = ValidationContext(df=df)
        rule = CheckRequiredColumns({
            "enabled": True,
            "severity": "error",
            "message": "Missing column: {column}",
            "params": {"columns": ["ID", "Name", "Value"]}
        })

        result = rule.validate(context)

        assert result.passed is True

    def test_check_required_columns_missing(self):
        """Test when required column is missing."""
        df = pd.DataFrame({"ID": [1, 2, 3]})
        context = ValidationContext(df=df)
        rule = CheckRequiredColumns({
            "enabled": True,
            "severity": "error",
            "message": "Missing column: {column}",
            "params": {"columns": ["ID", "Name"]}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["total_issues"] == 1
        assert result.details["issues"][0]["column"] == "Name"
        assert result.details["issues"][0]["issue"] == "missing"

    def test_check_required_columns_all_null(self):
        """Test when required column exists but is all null."""
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "Name": [None, None, None],
        })
        context = ValidationContext(df=df)
        rule = CheckRequiredColumns({
            "enabled": True,
            "severity": "error",
            "message": "Column {column} is all NULL",
            "params": {"columns": ["ID", "Name"], "allow_all_null": False}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["issues"][0]["column"] == "Name"
        assert result.details["issues"][0]["issue"] == "all_null"

    def test_check_required_columns_allow_all_null(self):
        """Test when all null is allowed."""
        df = pd.DataFrame({
            "ID": [1, 2, 3],
            "Name": [None, None, None],
        })
        context = ValidationContext(df=df)
        rule = CheckRequiredColumns({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"columns": ["ID", "Name"], "allow_all_null": True}
        })

        result = rule.validate(context)

        assert result.passed is True


# =============================================================================
# POST-PROCESSING RULES TESTS
# =============================================================================

class TestCheckRowCount:
    """Test row count validation rule."""

    def test_check_row_count_valid(self):
        """Test when row count is within expected range."""
        df_source = pd.DataFrame({"A": [1, 2, 3]})
        df_processed = pd.DataFrame({"value": [1, 2, 3, 4, 5, 6]})  # 3 rows * 2 value_vars
        context = ValidationContext(
            df=None,
            df_source=df_source,
            df_processed=df_processed,
            value_vars=["Month1", "Month2"]
        )
        rule = CheckRowCount({
            "enabled": True,
            "severity": "error",
            "message": "Row count mismatch: expected {expected}, got {actual} (ratio: {ratio})",
            "params": {"min_ratio": 0.9, "max_ratio": 1.1}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert result.details["expected"] == 6
        assert result.details["actual"] == 6
        assert result.details["ratio"] == 1.0

    def test_check_row_count_too_few(self):
        """Test when actual rows are fewer than expected."""
        df_source = pd.DataFrame({"A": [1, 2, 3]})
        df_processed = pd.DataFrame({"value": [1, 2, 3]})  # Should be 6 rows
        context = ValidationContext(
            df=None,
            df_source=df_source,
            df_processed=df_processed,
            value_vars=["Month1", "Month2"]
        )
        rule = CheckRowCount({
            "enabled": True,
            "severity": "error",
            "message": "Row count mismatch: expected {expected}, got {actual} (ratio: {ratio})",
            "params": {"min_ratio": 0.9, "max_ratio": 1.1}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["expected"] == 6
        assert result.details["actual"] == 3
        assert result.details["ratio"] == 0.5

    def test_check_row_count_missing_context(self):
        """Test when context is missing."""
        context = ValidationContext(df=None)
        rule = CheckRowCount({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {}
        })

        result = rule.validate(context)

        assert result.passed is True  # Skipped
        assert "Skipped" in result.message


class TestCheckNumericConversion:
    """Test numeric conversion validation rule."""

    def test_check_numeric_conversion_success(self):
        """Test successful numeric conversion."""
        df = pd.DataFrame({"Amount": [100, 200, 300, 400, 500]})
        context = ValidationContext(df=None, df_processed=df, value_name="Amount")
        rule = CheckNumericConversion({
            "enabled": True,
            "severity": "error",
            "message": "Conversion failed for {null_count} values in {value_column} ({percent}%)",
            "params": {"max_null_ratio": 0.1}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert result.details["null_count"] == 0

    def test_check_numeric_conversion_failures(self):
        """Test when numeric conversion has failures."""
        df = pd.DataFrame({"Amount": [100, None, 300, None, 500]})
        context = ValidationContext(df=None, df_processed=df, value_name="Amount")
        rule = CheckNumericConversion({
            "enabled": True,
            "severity": "warning",
            "message": "Conversion failed for {null_count} values in {value_column} ({percent}%)",
            "params": {"max_null_ratio": 0.1}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["null_count"] == 2
        assert result.details["null_ratio"] == 0.4

    def test_check_numeric_conversion_missing_column(self):
        """Test when value column is missing."""
        df = pd.DataFrame({"Other": [1, 2, 3]})
        context = ValidationContext(df=None, df_processed=df, value_name="Amount")
        rule = CheckNumericConversion({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert "not found" in result.message


class TestCheckOutliers:
    """Test outlier detection rule."""

    def test_check_outliers_zscore_no_outliers(self):
        """Test z-score method with no outliers."""
        df = pd.DataFrame({"Value": [10, 12, 11, 13, 12, 11]})
        context = ValidationContext(df=None, df_processed=df, value_name="Value")
        rule = CheckOutliers({
            "enabled": True,
            "severity": "warning",
            "message": "{count} outliers detected",
            "params": {"method": "zscore", "threshold": 3.0}
        })

        result = rule.validate(context)

        assert result.passed is True

    def test_check_outliers_zscore_with_outliers(self):
        """Test z-score method with outliers."""
        df = pd.DataFrame({"Value": [10, 11, 12, 11, 10, 100]})  # 100 is outlier
        context = ValidationContext(df=None, df_processed=df, value_name="Value")
        rule = CheckOutliers({
            "enabled": True,
            "severity": "warning",
            "message": "{count} outliers detected",
            "params": {"method": "zscore", "threshold": 2.0}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["outlier_count"] > 0

    def test_check_outliers_iqr_method(self):
        """Test IQR method for outlier detection."""
        df = pd.DataFrame({"Value": [10, 12, 11, 13, 12, 50]})  # 50 is outlier
        context = ValidationContext(df=None, df_processed=df, value_name="Value")
        rule = CheckOutliers({
            "enabled": True,
            "severity": "warning",
            "message": "{count} outliers detected",
            "params": {"method": "iqr", "threshold": 1.5}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["method"] == "iqr"
        assert result.details["outlier_count"] > 0

    def test_check_outliers_no_numeric_values(self):
        """Test with no numeric values."""
        df = pd.DataFrame({"Value": ["a", "b", "c"]})
        context = ValidationContext(df=None, df_processed=df, value_name="Value")
        rule = CheckOutliers({
            "enabled": True,
            "severity": "warning",
            "message": "",
            "params": {"method": "zscore"}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert "No numeric values" in result.message


class TestCheckDataCompleteness:
    """Test data completeness validation rule."""

    def test_check_data_completeness_complete(self):
        """Test when all combinations have complete data."""
        df = pd.DataFrame({
            "Site": ["A", "A", "A", "B", "B", "B"],
            "Month": ["Jan", "Feb", "Mar", "Jan", "Feb", "Mar"],
            "Value": [10, 20, 30, 40, 50, 60],
        })
        context = ValidationContext(df=None, df_processed=df, var_name="Month")
        rule = CheckDataCompleteness({
            "enabled": True,
            "severity": "warning",
            "message": "Missing data in {dimension_values}: expected {expected}, got {actual}",
            "params": {
                "dimensions": ["Site"],
                "variable_column": "Month",
                "expected_values": ["Jan", "Feb", "Mar"]
            }
        })

        result = rule.validate(context)

        assert result.passed is True

    def test_check_data_completeness_missing(self):
        """Test when some combinations are missing data."""
        df = pd.DataFrame({
            "Site": ["A", "A", "B"],  # Site B missing Feb and Mar
            "Month": ["Jan", "Feb", "Jan"],
            "Value": [10, 20, 40],
        })
        context = ValidationContext(df=None, df_processed=df, var_name="Month")
        rule = CheckDataCompleteness({
            "enabled": True,
            "severity": "warning",
            "message": "Missing data in {dimension_values}: expected {expected}, got {actual}",
            "params": {
                "dimensions": ["Site"],
                "variable_column": "Month",
                "expected_values": ["Jan", "Feb", "Mar"]
            }
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["total_issues"] == 2  # Site A and B both missing Mar

    def test_check_data_completeness_multiple_dimensions(self):
        """Test with multiple dimension columns."""
        df = pd.DataFrame({
            "Site": ["A", "A", "B", "B"],
            "Category": ["X", "Y", "X", "Y"],
            "Month": ["Jan", "Jan", "Jan", "Jan"],
            "Value": [10, 20, 30, 40],
        })
        context = ValidationContext(df=None, df_processed=df, var_name="Month")
        rule = CheckDataCompleteness({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {
                "dimensions": ["Site", "Category"],
                "variable_column": "Month",
                "expected_values": ["Jan", "Feb"]
            }
        })

        result = rule.validate(context)

        assert result.passed is False  # All missing Feb


class TestCheckTotalsMatch:
    """Test totals matching validation rule."""

    def test_check_totals_match_exact(self):
        """Test when totals match exactly."""
        df_source = pd.DataFrame({
            "ID": [1, 2],
            "Jan": [100, 200],
            "Feb": [150, 250],
        })
        df_processed = pd.DataFrame({
            "ID": [1, 1, 2, 2],
            "Month": ["Jan", "Feb", "Jan", "Feb"],
            "Amount": [100, 150, 200, 250],
        })
        context = ValidationContext(
            df=None,
            df_source=df_source,
            df_processed=df_processed,
            value_vars=["Jan", "Feb"],
            value_name="Amount"
        )
        rule = CheckTotalsMatch({
            "enabled": True,
            "severity": "error",
            "message": "Totals mismatch: source={source_total}, processed={processed_total}, diff={difference}",
            "params": {"tolerance": 0.01}
        })

        result = rule.validate(context)

        assert result.passed is True
        assert result.details["source_total"] == 700.0
        assert result.details["processed_total"] == 700.0
        assert result.details["difference"] == 0.0

    def test_check_totals_match_within_tolerance(self):
        """Test when totals match within tolerance."""
        df_source = pd.DataFrame({"Jan": [100.004]})
        df_processed = pd.DataFrame({"Amount": [100.003]})
        context = ValidationContext(
            df=None,
            df_source=df_source,
            df_processed=df_processed,
            value_vars=["Jan"],
            value_name="Amount"
        )
        rule = CheckTotalsMatch({
            "enabled": True,
            "severity": "error",
            "message": "",
            "params": {"tolerance": 0.01}
        })

        result = rule.validate(context)

        assert result.passed is True

    def test_check_totals_match_exceed_tolerance(self):
        """Test when totals exceed tolerance."""
        df_source = pd.DataFrame({"Jan": [100]})
        df_processed = pd.DataFrame({"Amount": [95]})  # 5 unit difference
        context = ValidationContext(
            df=None,
            df_source=df_source,
            df_processed=df_processed,
            value_vars=["Jan"],
            value_name="Amount"
        )
        rule = CheckTotalsMatch({
            "enabled": True,
            "severity": "warning",
            "message": "Totals mismatch: source={source_total}, processed={processed_total}, diff={difference}",
            "params": {"tolerance": 1.0}
        })

        result = rule.validate(context)

        assert result.passed is False
        assert result.details["difference"] == 5.0


class TestRuleRegistry:
    """Test rule registry functionality."""

    def test_rule_registry_contains_all_rules(self):
        """Test that registry contains all expected rules."""
        expected_rules = [
            "check_null_values",
            "check_duplicates",
            "check_column_types",
            "check_value_ranges",
            "check_required_columns",
            "check_row_count",
            "check_numeric_conversion",
            "check_outliers",
            "check_data_completeness",
            "check_totals_match",
        ]

        for rule_name in expected_rules:
            assert rule_name in RULE_REGISTRY
            assert callable(RULE_REGISTRY[rule_name])

    def test_rule_registry_instantiation(self):
        """Test that rules can be instantiated from registry."""
        for rule_name, rule_class in RULE_REGISTRY.items():
            rule = rule_class({
            "enabled": True,
            "severity": "error",
            "message": "Test message",
            "params": {}
        })
            assert rule.enabled is True
            assert rule.severity == "error"
