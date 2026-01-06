"""Tests for utility functions."""
import pytest
from pathlib import Path
from depivot.utils import (
    parse_column_list,
    generate_output_filename,
    find_excel_files,
    is_summary_row,
    extract_release_date,
)


# =============================================================================
# PARSE COLUMN LIST TESTS
# =============================================================================

class TestParseColumnList:
    """Test column list parsing."""

    def test_parse_simple_list(self):
        """Test parsing simple comma-separated list."""
        result = parse_column_list("ID,Name,Date")
        assert result == ["ID", "Name", "Date"]

    def test_parse_with_spaces(self):
        """Test parsing with whitespace."""
        result = parse_column_list("ID, Name , Date")
        assert result == ["ID", "Name", "Date"]

    def test_parse_none(self):
        """Test parsing None returns empty list."""
        result = parse_column_list(None)
        assert result == []

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty list."""
        result = parse_column_list("")
        assert result == []

    def test_parse_single_column(self):
        """Test parsing single column."""
        result = parse_column_list("ID")
        assert result == ["ID"]

    def test_parse_with_trailing_comma(self):
        """Test parsing with trailing comma."""
        result = parse_column_list("ID,Name,")
        assert result == ["ID", "Name"]


# =============================================================================
# GENERATE OUTPUT FILENAME TESTS
# =============================================================================

class TestGenerateOutputFilename:
    """Test output filename generation."""

    def test_generate_default(self):
        """Test default suffix and format."""
        input_path = Path("data.xlsx")
        result = generate_output_filename(input_path)
        assert result.name == "data_unpivoted.xlsx"

    def test_generate_custom_suffix(self):
        """Test custom suffix."""
        input_path = Path("data.xlsx")
        result = generate_output_filename(input_path, suffix="_long")
        assert result.name == "data_long.xlsx"

    def test_generate_custom_format(self):
        """Test custom output format."""
        input_path = Path("data.xlsx")
        result = generate_output_filename(input_path, output_format="csv")
        assert result.name == "data_unpivoted.csv"

    def test_generate_with_path(self):
        """Test with full path preserves directory."""
        input_path = Path("/some/dir/data.xlsx")
        result = generate_output_filename(input_path)
        assert result.parent == Path("/some/dir")
        assert result.name == "data_unpivoted.xlsx"

    def test_generate_custom_all(self):
        """Test with custom suffix and format."""
        input_path = Path("report.xlsx")
        result = generate_output_filename(input_path, suffix="_processed", output_format="csv")
        assert result.name == "report_processed.csv"


# =============================================================================
# FIND EXCEL FILES TESTS
# =============================================================================

class TestFindExcelFiles:
    """Test finding Excel files."""

    @pytest.fixture
    def test_directory(self, tmp_path):
        """Create test directory with Excel files."""
        # Create some Excel files
        (tmp_path / "file1.xlsx").touch()
        (tmp_path / "file2.xlsx").touch()
        (tmp_path / "data.csv").touch()

        # Create subdirectory with more files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.xlsx").touch()
        (subdir / "file4.xlsx").touch()

        return tmp_path

    def test_find_default_pattern(self, test_directory):
        """Test finding with default pattern."""
        files = find_excel_files(test_directory)
        assert len(files) == 2
        assert all(f.suffix == ".xlsx" for f in files)

    def test_find_custom_pattern(self, test_directory):
        """Test finding with custom pattern."""
        files = find_excel_files(test_directory, pattern="*.csv")
        assert len(files) == 1
        assert files[0].suffix == ".csv"

    def test_find_recursive(self, test_directory):
        """Test recursive search."""
        files = find_excel_files(test_directory, recursive=True)
        assert len(files) == 4  # 2 in root + 2 in subdir
        assert all(f.suffix == ".xlsx" for f in files)

    def test_find_non_recursive(self, test_directory):
        """Test non-recursive search (default)."""
        files = find_excel_files(test_directory, recursive=False)
        assert len(files) == 2  # Only in root directory

    def test_find_sorted_order(self, test_directory):
        """Test files are returned sorted."""
        files = find_excel_files(test_directory)
        assert files == sorted(files)


# =============================================================================
# IS SUMMARY ROW TESTS
# =============================================================================

class TestIsSummaryRow:
    """Test summary row detection."""

    def test_detect_grand_total(self):
        """Test detecting 'Grand Total' row."""
        row = {"Site": "Grand Total", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_detect_total(self):
        """Test detecting 'Total' row."""
        row = {"Site": "Austin", "Category": "Total"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_detect_subtotal(self):
        """Test detecting 'Subtotal' row."""
        row = {"Site": "Subtotal", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_detect_sum(self):
        """Test detecting 'Sum' row."""
        row = {"Site": "Sum", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_detect_summary(self):
        """Test detecting 'Summary' row."""
        row = {"Site": "Summary", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        row = {"Site": "GRAND TOTAL", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True

    def test_normal_row(self):
        """Test normal row is not detected as summary."""
        row = {"Site": "Austin", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is False

    def test_custom_patterns(self):
        """Test custom summary patterns."""
        row = {"Site": "Custom Summary", "Category": "Labor"}
        patterns = ["custom", "other"]  # Patterns should be lowercase for matching
        assert is_summary_row(row, ["Site", "Category"], patterns) is True

    def test_custom_patterns_no_match(self):
        """Test custom patterns don't match default."""
        row = {"Site": "Total", "Category": "Labor"}
        patterns = ["Custom", "Special"]
        # With custom patterns, default patterns are not used
        assert is_summary_row(row, ["Site", "Category"], patterns) is False

    def test_partial_match(self):
        """Test partial string matching."""
        row = {"Site": "Region Grand Total", "Category": "Labor"}
        assert is_summary_row(row, ["Site", "Category"]) is True


# =============================================================================
# EXTRACT RELEASE DATE TESTS
# =============================================================================

class TestExtractReleaseDate:
    """Test release date extraction from filenames."""

    def test_extract_underscore_format(self):
        """Test extracting YYYY_MM format."""
        result = extract_release_date("2025_02_All Sites.xlsx")
        assert result == "2025-02"

    def test_extract_hyphen_format(self):
        """Test extracting YYYY-MM format."""
        result = extract_release_date("2025-02-All Sites.xlsx")
        assert result == "2025-02"

    def test_extract_compact_format(self):
        """Test extracting YYYYMM format."""
        result = extract_release_date("202502_data.xlsx")
        assert result == "2025-02"

    def test_extract_no_date(self):
        """Test filename without date returns None."""
        result = extract_release_date("data.xlsx")
        assert result is None

    def test_extract_text_month(self):
        """Test filename with text month returns None."""
        result = extract_release_date("February 2025 Data.xlsx")
        assert result is None

    def test_extract_invalid_month(self):
        """Test YYYYMM with invalid month returns None."""
        result = extract_release_date("202513_data.xlsx")  # Month 13 is invalid
        assert result is None

    def test_extract_month_boundary_valid(self):
        """Test valid month boundaries (01 and 12)."""
        assert extract_release_date("202501_data.xlsx") == "2025-01"
        assert extract_release_date("202512_data.xlsx") == "2025-12"

    def test_extract_month_boundary_invalid(self):
        """Test invalid month boundaries (00 and 13)."""
        assert extract_release_date("202500_data.xlsx") is None
        assert extract_release_date("202513_data.xlsx") is None

    def test_extract_multiple_dates_uses_first(self):
        """Test multiple dates in filename uses first match."""
        result = extract_release_date("2025-01_report_2025-02.xlsx")
        assert result == "2025-01"

    def test_extract_date_in_middle(self):
        """Test date in middle of filename."""
        result = extract_release_date("Budget_2025-06_Final.xlsx")
        assert result == "2025-06"
