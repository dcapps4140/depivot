# Depivot - Technical Development Documentation

## Project Overview

**Purpose**: A production-grade Python CLI tool for transforming Excel data from wide (pivoted) format to long (unpivoted) format, designed specifically for processing Intel monthly data releases for SQL Server database import.

**Primary Use Case**: Process monthly financial/operational data releases (Actuals, Budget, Forecast) from multiple Excel files and combine them into a single, validated, database-ready output with full traceability.

## Key Features

### 1. Multi-Sheet Processing
- Process all sheets within a workbook or select specific sheets
- Option to combine all sheets into a single output worksheet
- Preserves sheet names in validation for traceability

### 2. Multi-File Wildcard Processing
- Process multiple files matching a wildcard pattern (e.g., `2025_*_All Sites EAC*.xlsx`)
- Combine data from multiple files into single output
- Automatic release date extraction from filenames (YYYY_MM or YYYY-MM patterns)
- Supports bash environments with escaped wildcards (`\*`)

### 3. Data Type Classification
- Automatic detection of Actual/Budget/Forecast from sheet names
- Manual override capability (`--data-type-override`)
- Forecast split logic: marks months >= forecast-start as "Forecast", prior months as "Actual"
- Adds `DataType` column for database categorization

### 4. Release Date Tracking
- Automatically extracts release date from filename patterns (2025_02, 2025-02, 202502)
- Manual override via `--release-date` parameter
- Adds `ReleaseDate` column to track which data release each row belongs to
- Critical for maintaining data lineage across monthly updates

### 5. Data Validation & Quality Assurance
- Automatic validation report generated for every run
- Validates totals: source vs processed data at row, sheet, and grand total levels
- Validation report includes `SourceFile` column for investigation
- Reports mismatches (e.g., summary rows like "Grand Total" in source data)
- Can be disabled with `--no-validate` flag

### 6. Numeric Value Cleaning
- Handles special characters, currency symbols
- Preserves decimal precision (critical for financial data)
- Converts negative numbers in parentheses: `(123.45)` → `-123.45`
- Removes commas from formatted numbers: `1,234.56` → `1234.56`

### 7. Flexible Column Handling
- Auto-generates row index if no ID columns specified
- Include/exclude column filters
- Value column auto-detection (all non-ID columns)
- Handles complex column structures (e.g., Budget columns with `.1` suffix)

## Architecture & Design Decisions

### File Structure
```
depivot/
├── src/depivot/
│   ├── __init__.py           # Package initialization
│   ├── __main__.py           # Enable 'python -m depivot'
│   ├── cli.py                # Click CLI interface - entry point
│   ├── core.py               # Core business logic
│   ├── validators.py         # Input validation functions
│   ├── exceptions.py         # Custom exception hierarchy
│   └── utils.py              # Helper utilities
├── pyproject.toml            # Modern Python project config
├── requirements.txt          # Dependencies
├── README.md                 # User documentation
└── DEVELOPMENT.md            # This file
```

### Key Design Patterns

**Separation of Concerns**:
- `cli.py`: User interface, argument parsing, workflow orchestration
- `core.py`: Business logic, data transformation, validation
- `validators.py`: Input validation (fail-fast principle)
- `utils.py`: Reusable utilities (file discovery, parsing, date extraction)

**Fail-Fast Validation**:
- Validate all inputs before processing
- Clear error messages with context (e.g., list available sheets when sheet not found)

**src-layout**:
- Prevents import issues during development
- Cleaner packaging and distribution

### Technology Stack

**Core Dependencies**:
- `click>=8.1.0` - CLI framework (decorator-based, intuitive)
- `pandas>=2.0.0` - Data manipulation using battle-tested `melt()` function
- `openpyxl>=3.1.0` - Excel I/O (.xlsx support)
- `rich>=13.0.0` - Beautiful terminal output, progress bars, colored text

**Why pandas.melt()**:
- Industry standard for unpivoting operations
- Handles complex data types correctly
- Preserves data integrity
- Well-tested and performant

## Critical Implementation Details

### 1. Wildcard Processing in Bash Environments

**Problem**: Bash automatically expands glob patterns before passing to Python, causing Click to receive multiple file arguments instead of a pattern string.

**Solution**:
- Changed `input_path` from `click.Path()` to `str` type
- Users escape wildcards: `2025_\*_All Sites EAC\*.xlsx`
- Code unescapes before passing to `glob.glob()`

```python
# In cli.py
has_wildcards = '*' in input_path_str or '?' in input_path_str
if has_wildcards:
    unescaped_pattern = input_path_str.replace(r'\*', '*').replace(r'\?', '?')
    matching_files = [Path(f) for f in glob(unescaped_pattern) if Path(f).is_file()]
```

**Note**: Windows CMD/PowerShell users don't need to escape wildcards.

### 2. Release Date Extraction

**Patterns Supported**:
- `YYYY_MM`: 2025_02
- `YYYY-MM`: 2025-02
- `YYYYMM`: 202502 (validates month is 01-12)

**Implementation** (`utils.py:extract_release_date()`):
```python
# Try YYYY_MM or YYYY-MM
match = re.search(r'(\d{4})[_-](\d{2})', filename)
if match:
    year, month = match.groups()
    return f"{year}-{month}"

# Try YYYYMM
match = re.search(r'(\d{4})(\d{2})', filename)
if match:
    year, month = match.groups()
    if 1 <= int(month) <= 12:
        return f"{year}-{month}"
```

### 3. Forecast Month Logic

**Requirement**: Split Actual data into Actual (historical) vs Forecast (future) based on a threshold month.

**Example**: If `--forecast-start "March"`, then:
- Jan, Feb = "Actual"
- Mar, Apr, May, ... Dec = "Forecast"

**Implementation** (`core.py:is_forecast_month()`):
```python
MONTH_ORDER = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def is_forecast_month(month: str, forecast_start: str) -> bool:
    month_lower = month.lower()[:3]
    forecast_lower = forecast_start.lower()[:3]
    month_num = MONTH_ORDER.get(month_lower, 0)
    forecast_num = MONTH_ORDER.get(forecast_lower, 0)
    return month_num >= forecast_num
```

### 4. Numeric Value Cleaning

**Why Needed**: Excel data often has:
- Currency symbols: `$1,234.56`
- Thousands separators: `1,234.56`
- Negative in parentheses: `(123.45)` means `-123.45`
- Special characters from formatting

**Implementation** (`core.py:clean_numeric_value()`):
```python
def clean_numeric_value(value) -> float:
    if pd.isna(value):
        return float('nan')
    if isinstance(value, (int, float)):
        return float(value)

    value_str = str(value)
    # Remove special chars (keep digits, decimal, comma, parens, minus)
    value_str = re.sub(r'[^\d.,()\-]', '', value_str)

    # Handle negative in parentheses
    is_negative = '(' in value_str and ')' in value_str
    if is_negative:
        value_str = value_str.replace('(', '').replace(')', '')

    value_str = value_str.replace(',', '')

    try:
        result = float(value_str)
        return -result if is_negative else result
    except (ValueError, AttributeError):
        return float('nan')
```

### 5. Validation Report Structure

**Validation Levels**:
1. **Row-level**: Each Site/Category combination's totals (source vs processed)
2. **Sheet-level**: `SHEET_TOTAL` - sum of all data in a sheet
3. **Grand-level**: `GRAND_TOTAL` - sum across all sheets/files

**Critical Validation**:
- **SHEET_TOTAL** and **GRAND_TOTAL** rows with `Match = "OK"` confirm data integrity
- Mismatches usually indicate summary rows in source (e.g., "Grand Total" row)

**Validation Columns**:
- `SourceFile`: Which file this validation row came from
- `Sheet`: Which sheet
- `Site`, `Category`: ID columns (if applicable)
- `Source_Total`: Sum of all value columns in source row
- `Processed_Total`: Sum of all Amount values for this Site/Category in output
- `Difference`: Processed - Source (should be ~0)
- `Match`: "OK" if abs(Difference) < 0.01, else "MISMATCH"

### 6. Multi-File Processing Flow

**Function**: `depivot_multi_file()` in `core.py`

**Flow**:
1. Loop through each input file
2. For each file:
   - Process each sheet (read, depivot, clean, add DataType, ReleaseDate)
   - Generate validation for this file
3. Combine all depivoted data into single DataFrame
4. Combine all validation data
5. Write to Excel:
   - "Data" sheet: combined data (no SourceFile/SourceSheet - keeps it clean)
   - "Validation" sheet: validation with SourceFile for traceability

## Common Usage Patterns

### Process Single File with Actuals Section
```bash
depivot "W:\Intel Data\2025_02_All Sites.xlsx" \
  "W:\Intel Data\2025_02_Actuals.xlsx" \
  --id-vars "Site,Category" \
  --value-vars "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec" \
  --var-name "Month" \
  --value-name "Amount" \
  --forecast-start "March" \
  --data-type-override "Actual" \
  --sheet-names "Workings - Actuals & Budgets" \
  --header-row 2 \
  --verbose
```

### Process Multiple Files with Wildcard (Bash)
```bash
depivot "W:\Intel Data\2025_\*_All Sites EAC\*.xlsx" \
  "W:\Intel Data\All_Actuals_2025.xlsx" \
  --id-vars "Site,Category" \
  --value-vars "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec" \
  --var-name "Month" \
  --value-name "Amount" \
  --forecast-start "March" \
  --data-type-override "Actual" \
  --sheet-names "Workings - Actuals & Budgets" \
  --header-row 2 \
  --verbose
```

**Note**: Escape wildcards with backslashes (`\*`) in bash environments.

### Process Budget Section
```bash
depivot "W:\Intel Data\2025_\*_All Sites EAC\*.xlsx" \
  "W:\Intel Data\All_Budget_2025.xlsx" \
  --id-vars "Site.1,Category.1" \
  --value-vars "Jan.1,Feb.1,Mar.1,Apr.1,May.1,Jun.1,Jul.1,Aug.1,Sep.1,Oct.1,Nov.1,Dec.1" \
  --var-name "Month" \
  --value-name "Amount" \
  --data-type-override "Budget" \
  --sheet-names "Workings - Actuals & Budgets" \
  --header-row 2 \
  --verbose
```

**Note**: Budget columns have `.1` suffix (Site.1, Jan.1, etc.) because they're in the same sheet as Actuals.

## Development History

### Phase 1: Foundation
- Project structure, dependencies, basic CLI
- Single-file, single-sheet depivoting
- pandas.melt() integration

### Phase 2: Multi-Sheet Support
- Process all sheets in a workbook
- Output as separate sheets in one file
- Sheet name filtering (--sheet-names, --skip-sheets)

### Phase 3: Production Requirements
- No ID columns support (auto-generate row index)
- DataType column with auto-detection
- Forecast split logic
- Decimal preservation (clean_numeric_value)

### Phase 4: Data Lineage & Validation
- Release date extraction and tracking
- Validation report generation
- SourceFile column in validation
- --no-validate flag

### Phase 5: Multi-File Processing
- Wildcard pattern support
- Bash glob expansion handling
- depivot_multi_file() implementation
- Combined output from multiple files

### Phase 6: UI Refinements
- --combine-sheets flag
- Removed SourceFile/SourceSheet from Data tab (keep in Validation only)
- --output-sheet-name option
- Better progress reporting

## Important Notes for Future Developers

### Data Integrity
- **Never skip validation** unless absolutely necessary
- **Always preserve decimals** - financial data requires precision
- **Test with actual Intel data** - synthetic data may not catch real-world issues

### Excel Quirks
- Some sheets have title rows (use --header-row to skip)
- Side-by-side data sections need different column specs (Site vs Site.1)
- Summary rows (Grand Total) will appear as mismatches - this is expected
- Always use openpyxl engine for .xlsx files

### Performance Considerations
- Processing 10 files × 161 rows × 12 months = 19,320 output rows is fast (<10 seconds)
- Validation adds minimal overhead
- Most time is spent in Excel I/O, not pandas operations

### Common Pitfalls
1. **Forgetting to escape wildcards in bash** - command will fail with "unexpected extra arguments"
2. **Wrong header row** - causes "Column not found" errors
3. **Mixing Actuals and Budget columns** - use separate commands for each
4. **Not specifying output path for wildcards** - required for multi-file processing

## Testing Strategy

### Manual Testing Checklist
- [ ] Single file, single sheet
- [ ] Single file, multiple sheets
- [ ] Wildcard with multiple files
- [ ] --combine-sheets flag
- [ ] --forecast-start logic
- [ ] Decimal preservation
- [ ] Validation report accuracy
- [ ] Release date extraction
- [ ] Edge cases: blank rows, summary rows, NaN values

### Test Data
- Use actual Intel data files from `W:\Intel Data\`
- Files: `2025_02_All Sites EAC Budget vs Actuals (Forecast Updates).xlsx`
- Expected output: 161 rows → 1,932 rows per sheet per file

## Future Enhancements

### Potential Improvements
1. **Row filtering** - exclude summary rows like "Grand Total" automatically
2. **SQL Server direct upload** - integrate with sqlalchemy
3. **Configuration files** - save commonly used parameter sets
4. **Parallel processing** - process multiple files concurrently
5. **Data quality rules** - flag anomalies (negative values where unexpected, etc.)
6. **Excel template validation** - verify input files match expected structure
7. **Incremental updates** - only process new/changed files

### Architecture Considerations
- Consider adding a database layer (models.py)
- May need async processing for very large datasets
- Could benefit from a configuration management system

## Maintenance

### When to Update
- **New data structure** - update column mappings
- **New data types** - extend detect_data_type()
- **New validation rules** - extend create_validation_report()
- **Performance issues** - profile with cProfile, optimize bottlenecks

### Backward Compatibility
- Maintain existing CLI interface (don't break scripts)
- Add new features as opt-in flags
- Deprecate old features gracefully with warnings

## Contact & Support

For questions about implementation details, contact the development team or refer to:
- README.md for user-facing documentation
- Code comments and docstrings for function-level details
- Git commit history for change rationale

---

**Last Updated**: December 31, 2025
**Version**: 0.1.0
**Python Version**: 3.8+
