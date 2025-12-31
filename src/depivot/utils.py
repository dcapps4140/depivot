"""Helper utilities for depivot."""

import re
from pathlib import Path
from typing import List, Optional


def parse_column_list(column_str: Optional[str]) -> List[str]:
    """Parse comma-separated column string into list.

    Args:
        column_str: Comma-separated column names (e.g., "ID,Name,Date")

    Returns:
        List of column names with whitespace stripped

    Examples:
        >>> parse_column_list("ID, Name, Date")
        ['ID', 'Name', 'Date']
        >>> parse_column_list(None)
        []
    """
    if not column_str:
        return []
    return [col.strip() for col in column_str.split(",") if col.strip()]


def generate_output_filename(
    input_path: Path, suffix: str = "_unpivoted", output_format: str = "xlsx"
) -> Path:
    """Generate output filename with suffix and format.

    Args:
        input_path: Path to input file
        suffix: Suffix to add to filename (default: "_unpivoted")
        output_format: Output file format (default: "xlsx")

    Returns:
        Path object for output file

    Examples:
        >>> generate_output_filename(Path("data.xlsx"))
        PosixPath('data_unpivoted.xlsx')
        >>> generate_output_filename(Path("data.xlsx"), "_long", "csv")
        PosixPath('data_long.csv')
    """
    return input_path.parent / f"{input_path.stem}{suffix}.{output_format}"


def find_excel_files(
    directory: Path, pattern: str = "*.xlsx", recursive: bool = False
) -> List[Path]:
    """Find Excel files matching pattern in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern (default: "*.xlsx")
        recursive: Search subdirectories recursively (default: False)

    Returns:
        List of Path objects for matching files

    Examples:
        >>> find_excel_files(Path("/data"), "*.xlsx")
        [PosixPath('/data/file1.xlsx'), PosixPath('/data/file2.xlsx')]
    """
    if recursive:
        return sorted(directory.rglob(pattern))
    return sorted(directory.glob(pattern))


def extract_release_date(filename: str) -> Optional[str]:
    """Extract release date from filename.

    Looks for patterns like:
    - YYYY_MM (e.g., "2025_02")
    - YYYY-MM (e.g., "2025-02")
    - YYYYMM (e.g., "202502")

    Args:
        filename: Filename to extract date from

    Returns:
        Release date in YYYY-MM format, or None if not found

    Examples:
        >>> extract_release_date("2025_02_All Sites.xlsx")
        '2025-02'
        >>> extract_release_date("February 2025 Data.xlsx")
        None
    """
    # Try YYYY_MM or YYYY-MM pattern
    match = re.search(r'(\d{4})[_-](\d{2})', filename)
    if match:
        year, month = match.groups()
        return f"{year}-{month}"

    # Try YYYYMM pattern (6 consecutive digits)
    match = re.search(r'(\d{4})(\d{2})', filename)
    if match:
        year, month = match.groups()
        # Validate month is between 01-12
        if 1 <= int(month) <= 12:
            return f"{year}-{month}"

    return None
