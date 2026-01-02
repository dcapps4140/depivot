"""
Individual validation rule implementations.

Provides concrete validation rules for pre-processing and post-processing checks.
"""
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import numpy as np

from depivot.data_quality import ValidationContext, ValidationResult, ValidationRule


# =============================================================================
# PRE-PROCESSING RULES
# =============================================================================

class CheckNullValues(ValidationRule):
    """Check for excessive NULL values in columns."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Validate NULL/missing value ratios in specified columns.

        Params:
            columns: List of column names or "all" for all columns
            threshold: Float 0.0-1.0 (ratio of NULLs allowed)
            per_column: Boolean (report per-column or aggregate)

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df
        columns = self.params.get("columns", "all")
        threshold = self.params.get("threshold", 0.05)
        per_column = self.params.get("per_column", True)

        if columns == "all":
            columns = df.columns.tolist()

        issues = []
        for col in columns:
            if col not in df.columns:
                continue

            null_count = df[col].isna().sum()
            null_ratio = null_count / len(df) if len(df) > 0 else 0

            if null_ratio > threshold:
                issues.append({
                    "column": col,
                    "null_count": int(null_count),
                    "null_ratio": float(null_ratio),
                    "threshold": threshold
                })

        if issues:
            # Format message for first issue
            first = issues[0]
            message = self.format_message(
                column=first["column"],
                percent=f"{first['null_ratio']*100:.2f}",
                threshold=f"{threshold*100:.0f}"
            )

            return ValidationResult(
                rule_name="check_null_values",
                severity=self.severity,
                passed=False,
                message=message,
                details={"issues": issues, "total_issues": len(issues)},
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_null_values",
            severity=self.severity,
            passed=True,
            message="No excessive NULL values detected",
            details={},
            timestamp=datetime.now()
        )


class CheckDuplicates(ValidationRule):
    """Check for duplicate rows."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Detect duplicate rows based on key columns.

        Params:
            key_columns: List of column names defining uniqueness
                         (or None/empty for full row duplicates)

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df
        key_columns = self.params.get("key_columns", None)

        if key_columns:
            # Check duplicates on key columns
            duplicates = df[df.duplicated(subset=key_columns, keep=False)]
        else:
            # Check entire row duplicates
            duplicates = df[df.duplicated(keep=False)]

        dup_count = len(duplicates)

        if dup_count > 0:
            message = self.format_message(count=dup_count)

            # Sample duplicates for details
            sample_dups = duplicates.head(5).to_dict('records')

            return ValidationResult(
                rule_name="check_duplicates",
                severity=self.severity,
                passed=False,
                message=message,
                details={
                    "duplicate_count": dup_count,
                    "key_columns": key_columns,
                    "sample_duplicates": sample_dups
                },
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_duplicates",
            severity=self.severity,
            passed=True,
            message="No duplicates detected",
            details={},
            timestamp=datetime.now()
        )


class CheckColumnTypes(ValidationRule):
    """Validate expected data types."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Check columns match expected semantic types.

        Params:
            type_specs: Dict mapping column names to expected types
                        ("string", "numeric", "datetime")

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df
        type_specs = self.params.get("type_specs", {})

        issues = []
        for col, expected_type in type_specs.items():
            if col not in df.columns:
                issues.append({
                    "column": col,
                    "issue": "missing",
                    "expected": expected_type,
                    "actual": None
                })
                continue

            actual_type = self._infer_type(df[col])
            if actual_type != expected_type:
                issues.append({
                    "column": col,
                    "expected": expected_type,
                    "actual": actual_type,
                    "issue": "type_mismatch"
                })

        if issues:
            first = issues[0]
            message = self.format_message(
                column=first["column"],
                expected=first["expected"],
                actual=first.get("actual", "missing")
            )

            return ValidationResult(
                rule_name="check_column_types",
                severity=self.severity,
                passed=False,
                message=message,
                details={"issues": issues, "total_issues": len(issues)},
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_column_types",
            severity=self.severity,
            passed=True,
            message="All column types match expected",
            details={},
            timestamp=datetime.now()
        )

    def _infer_type(self, series: pd.Series) -> str:
        """Infer semantic type of series."""
        # Try numeric conversion
        try:
            pd.to_numeric(series.dropna(), errors='raise')
            return "numeric"
        except (ValueError, TypeError):
            pass

        # Try datetime
        try:
            pd.to_datetime(series.dropna(), errors='raise')
            return "datetime"
        except (ValueError, TypeError, pd.errors.ParserError):
            pass

        return "string"


class CheckValueRanges(ValidationRule):
    """Check values are within expected ranges."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Detect values outside expected min/max ranges.

        Params:
            ranges: Dict mapping columns to range specs
                    e.g., {"Jan": {"min": 0, "max": 1000000}}

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df
        ranges = self.params.get("ranges", {})

        issues = []
        for col, range_spec in ranges.items():
            if col not in df.columns:
                continue

            min_val = range_spec.get("min", None)
            max_val = range_spec.get("max", None)

            # Convert to numeric
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                continue

            outliers = pd.Series([False] * len(df))
            if min_val is not None:
                outliers |= numeric_col < min_val
            if max_val is not None:
                outliers |= numeric_col > max_val

            outlier_count = outliers.sum()

            if outlier_count > 0:
                issues.append({
                    "column": col,
                    "outlier_count": int(outlier_count),
                    "min": min_val,
                    "max": max_val,
                    "actual_min": float(numeric_col.min()) if not numeric_col.isna().all() else None,
                    "actual_max": float(numeric_col.max()) if not numeric_col.isna().all() else None
                })

        if issues:
            first = issues[0]
            message = self.format_message(
                column=first["column"],
                count=first["outlier_count"]
            )

            return ValidationResult(
                rule_name="check_value_ranges",
                severity=self.severity,
                passed=False,
                message=message,
                details={"issues": issues, "total_issues": len(issues)},
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_value_ranges",
            severity=self.severity,
            passed=True,
            message="All values within expected ranges",
            details={},
            timestamp=datetime.now()
        )


class CheckRequiredColumns(ValidationRule):
    """Ensure required columns exist and are non-empty."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Check required columns are present and populated.

        Params:
            columns: List of required column names
            allow_all_null: Boolean (allow column to exist but be all NULL)

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df
        required_columns = self.params.get("columns", [])
        allow_all_null = self.params.get("allow_all_null", False)

        issues = []
        for col in required_columns:
            if col not in df.columns:
                issues.append({
                    "column": col,
                    "issue": "missing"
                })
            elif not allow_all_null and df[col].isna().all():
                issues.append({
                    "column": col,
                    "issue": "all_null"
                })

        if issues:
            first = issues[0]
            message = self.format_message(column=first["column"])

            return ValidationResult(
                rule_name="check_required_columns",
                severity=self.severity,
                passed=False,
                message=message,
                details={"issues": issues, "total_issues": len(issues)},
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_required_columns",
            severity=self.severity,
            passed=True,
            message="All required columns present",
            details={},
            timestamp=datetime.now()
        )


# =============================================================================
# POST-PROCESSING RULES
# =============================================================================

class CheckRowCount(ValidationRule):
    """Validate row count matches expectations after depivot."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Check depivoted row count is within expected range.

        Expected rows = source_rows × num_value_columns

        Params:
            min_ratio: Float (minimum ratio of actual/expected)
            max_ratio: Float (maximum ratio of actual/expected)

        Returns:
            ValidationResult with pass/fail and details
        """
        df_source = context.df_source
        df_processed = context.df_processed
        value_vars = context.value_vars

        if df_source is None or df_processed is None:
            return ValidationResult(
                rule_name="check_row_count",
                severity="warning",
                passed=True,
                message="Skipped (missing context)",
                details={},
                timestamp=datetime.now()
            )

        expected_rows = len(df_source) * len(value_vars)
        actual_rows = len(df_processed)
        ratio = actual_rows / expected_rows if expected_rows > 0 else 0

        min_ratio = self.params.get("min_ratio", 0.9)
        max_ratio = self.params.get("max_ratio", 1.1)

        if not (min_ratio <= ratio <= max_ratio):
            message = self.format_message(
                expected=expected_rows,
                actual=actual_rows,
                ratio=f"{ratio:.2f}"
            )

            return ValidationResult(
                rule_name="check_row_count",
                severity=self.severity,
                passed=False,
                message=message,
                details={
                    "expected": expected_rows,
                    "actual": actual_rows,
                    "ratio": float(ratio),
                    "min_ratio": min_ratio,
                    "max_ratio": max_ratio
                },
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_row_count",
            severity=self.severity,
            passed=True,
            message=f"Row count valid: {actual_rows} rows ({ratio:.2f}x expected)",
            details={"actual": actual_rows, "expected": expected_rows, "ratio": float(ratio)},
            timestamp=datetime.now()
        )


class CheckNumericConversion(ValidationRule):
    """Check for numeric conversion failures (NULLs in value column)."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Track numeric conversion success rate.

        Params:
            value_column: Name of value column (defaults to context.value_name)
            max_null_ratio: Float (maximum acceptable NULL ratio)

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df_processed
        if df is None:
            return ValidationResult(
                rule_name="check_numeric_conversion",
                severity="warning",
                passed=True,
                message="Skipped (missing context)",
                details={},
                timestamp=datetime.now()
            )

        value_column = self.params.get("value_column", context.value_name)
        max_null_ratio = self.params.get("max_null_ratio", 0.1)

        if value_column not in df.columns:
            return ValidationResult(
                rule_name="check_numeric_conversion",
                severity="error",
                passed=False,
                message=f"Value column '{value_column}' not found",
                details={},
                timestamp=datetime.now()
            )

        null_count = df[value_column].isna().sum()
        null_ratio = null_count / len(df) if len(df) > 0 else 0

        if null_ratio > max_null_ratio:
            message = self.format_message(
                null_count=int(null_count),
                value_column=value_column,
                percent=f"{null_ratio*100:.2f}"
            )

            return ValidationResult(
                rule_name="check_numeric_conversion",
                severity=self.severity,
                passed=False,
                message=message,
                details={
                    "null_count": int(null_count),
                    "null_ratio": float(null_ratio),
                    "max_null_ratio": max_null_ratio,
                    "value_column": value_column
                },
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_numeric_conversion",
            severity=self.severity,
            passed=True,
            message=f"Numeric conversion successful: {null_ratio*100:.2f}% NULLs",
            details={"null_count": int(null_count), "null_ratio": float(null_ratio)},
            timestamp=datetime.now()
        )


class CheckOutliers(ValidationRule):
    """Detect statistical outliers in depivoted data."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Identify statistical outliers using specified method.

        Params:
            value_column: Column to analyze
            method: "zscore" | "iqr" | "percentile"
            threshold: Float (depends on method)
                - zscore: standard deviations (e.g., 3.0)
                - iqr: IQR multiplier (e.g., 1.5)
                - percentile: not implemented yet

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df_processed
        if df is None:
            return ValidationResult(
                rule_name="check_outliers",
                severity="warning",
                passed=True,
                message="Skipped (missing context)",
                details={},
                timestamp=datetime.now()
            )

        value_column = self.params.get("value_column", context.value_name)
        method = self.params.get("method", "zscore")
        threshold = self.params.get("threshold", 3.0)

        if value_column not in df.columns:
            return ValidationResult(
                rule_name="check_outliers",
                severity="warning",
                passed=True,
                message=f"Value column '{value_column}' not found",
                details={},
                timestamp=datetime.now()
            )

        # Convert to numeric
        numeric_col = pd.to_numeric(df[value_column], errors='coerce').dropna()

        if len(numeric_col) == 0:
            return ValidationResult(
                rule_name="check_outliers",
                severity="warning",
                passed=True,
                message="No numeric values to check",
                details={},
                timestamp=datetime.now()
            )

        outlier_count = 0
        if method == "zscore":
            mean = numeric_col.mean()
            std = numeric_col.std()
            if std > 0:
                z_scores = np.abs((numeric_col - mean) / std)
                outlier_count = (z_scores > threshold).sum()

        elif method == "iqr":
            Q1 = numeric_col.quantile(0.25)
            Q3 = numeric_col.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            outlier_count = ((numeric_col < lower_bound) | (numeric_col > upper_bound)).sum()

        if outlier_count > 0:
            message = self.format_message(count=int(outlier_count))

            return ValidationResult(
                rule_name="check_outliers",
                severity=self.severity,
                passed=False,
                message=message,
                details={
                    "outlier_count": int(outlier_count),
                    "method": method,
                    "threshold": threshold,
                    "value_column": value_column
                },
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_outliers",
            severity=self.severity,
            passed=True,
            message=f"No outliers detected (method: {method}, threshold: {threshold})",
            details={"method": method, "threshold": threshold},
            timestamp=datetime.now()
        )


class CheckDataCompleteness(ValidationRule):
    """Check for missing combinations of categorical variables."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Detect missing data in expected dimension combinations.

        Params:
            dimensions: List of grouping columns (e.g., ["Site", "Category"])
            variable_column: Column that should have all expected values
            expected_values: List of expected values in variable_column

        Returns:
            ValidationResult with pass/fail and details
        """
        df = context.df_processed
        if df is None:
            return ValidationResult(
                rule_name="check_data_completeness",
                severity="warning",
                passed=True,
                message="Skipped (missing context)",
                details={},
                timestamp=datetime.now()
            )

        dimensions = self.params.get("dimensions", [])
        variable_column = self.params.get("variable_column", context.var_name)
        expected_values = set(self.params.get("expected_values", []))

        if not dimensions or not expected_values:
            return ValidationResult(
                rule_name="check_data_completeness",
                severity="warning",
                passed=True,
                message="Skipped (no dimensions or expected_values configured)",
                details={},
                timestamp=datetime.now()
            )

        # Check all required columns exist
        required_cols = dimensions + [variable_column]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return ValidationResult(
                rule_name="check_data_completeness",
                severity="warning",
                passed=True,
                message=f"Skipped (missing columns: {missing_cols})",
                details={},
                timestamp=datetime.now()
            )

        # Group by dimensions and check for missing values
        grouped = df.groupby(dimensions)[variable_column].apply(lambda x: set(x))

        issues = []
        for group_keys, values in grouped.items():
            missing = expected_values - values
            if missing:
                # group_keys can be a tuple or single value
                if isinstance(group_keys, tuple):
                    dim_values = ", ".join(f"{d}={v}" for d, v in zip(dimensions, group_keys))
                else:
                    dim_values = f"{dimensions[0]}={group_keys}"

                issues.append({
                    "dimension_values": dim_values,
                    "missing_values": sorted(list(missing)),
                    "found_values": sorted(list(values)),
                    "expected_values": sorted(list(expected_values))
                })

        if issues:
            first = issues[0]
            message = self.format_message(
                dimension_values=first["dimension_values"],
                expected=len(expected_values),
                actual=len(first["found_values"])
            )

            return ValidationResult(
                rule_name="check_data_completeness",
                severity=self.severity,
                passed=False,
                message=message,
                details={"issues": issues[:10], "total_issues": len(issues)},  # Limit details
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_data_completeness",
            severity=self.severity,
            passed=True,
            message="All dimension combinations have complete data",
            details={},
            timestamp=datetime.now()
        )


class CheckTotalsMatch(ValidationRule):
    """Enhanced validation - check if totals match between source and processed data."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Verify totals match between source and processed data.

        This enhances the existing validation report functionality
        with configurable error threshold.

        Params:
            tolerance: Float (absolute difference tolerance, default 0.01)

        Returns:
            ValidationResult with pass/fail and details
        """
        df_source = context.df_source
        df_processed = context.df_processed
        value_vars = context.value_vars
        value_name = context.value_name

        if df_source is None or df_processed is None:
            return ValidationResult(
                rule_name="check_totals_match",
                severity="warning",
                passed=True,
                message="Skipped (missing context)",
                details={},
                timestamp=datetime.now()
            )

        tolerance = self.params.get("tolerance", 0.01)

        # Calculate source total (sum of all value columns)
        try:
            source_total = df_source[value_vars].apply(pd.to_numeric, errors='coerce').sum().sum()
        except Exception:
            source_total = 0

        # Calculate processed total
        try:
            processed_total = pd.to_numeric(df_processed[value_name], errors='coerce').sum()
        except Exception:
            processed_total = 0

        difference = abs(source_total - processed_total)

        if difference > tolerance:
            message = self.format_message(
                source_total=f"{source_total:,.2f}",
                processed_total=f"{processed_total:,.2f}",
                difference=f"{difference:,.2f}"
            )

            return ValidationResult(
                rule_name="check_totals_match",
                severity=self.severity,
                passed=False,
                message=message,
                details={
                    "source_total": float(source_total),
                    "processed_total": float(processed_total),
                    "difference": float(difference),
                    "tolerance": tolerance
                },
                timestamp=datetime.now()
            )

        return ValidationResult(
            rule_name="check_totals_match",
            severity=self.severity,
            passed=True,
            message=f"Totals match within tolerance: diff={difference:.2f}",
            details={
                "source_total": float(source_total),
                "processed_total": float(processed_total),
                "difference": float(difference)
            },
            timestamp=datetime.now()
        )


# =============================================================================
# RULE REGISTRY
# =============================================================================

RULE_REGISTRY: Dict[str, type] = {
    # Pre-processing rules
    "check_null_values": CheckNullValues,
    "check_duplicates": CheckDuplicates,
    "check_column_types": CheckColumnTypes,
    "check_value_ranges": CheckValueRanges,
    "check_required_columns": CheckRequiredColumns,

    # Post-processing rules
    "check_row_count": CheckRowCount,
    "check_numeric_conversion": CheckNumericConversion,
    "check_outliers": CheckOutliers,
    "check_data_completeness": CheckDataCompleteness,
    "check_totals_match": CheckTotalsMatch,
}
