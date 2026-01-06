# Depivot

A Python CLI tool to unpivot/melt Excel files from wide format to long format with multi-worksheet support.

## What is Depivoting?

Depivoting (also called "melting" or "unpivoting") transforms data from wide format to long format:

**Wide Format (Before):**
```
ID | Name  | Month1 | Month2 | Month3
1  | Alice | 100    | 150    | 200
2  | Bob   | 120    | 130    | 140
```

**Long Format (After):**
```
ID | Name  | Month  | Value
1  | Alice | Month1 | 100
1  | Alice | Month2 | 150
1  | Alice | Month3 | 200
2  | Bob   | Month1 | 120
2  | Bob   | Month2 | 130
2  | Bob   | Month3 | 140
```

## Features

- Unpivot/melt Excel data from wide to long format
- Multi-worksheet support - process all sheets in a workbook
- Batch processing - process multiple files at once
- Column selection and filtering
- Row filtering - exclude summary/total rows automatically
- Configuration files - save and load parameter sets
- **SQL Server upload** - upload depivoted data directly to SQL Server
- **Template validation** - verify Excel file structure before processing
- **Data quality validation** - comprehensive pre/post-processing data checks
- Beautiful CLI with progress bars and colored output
- Flexible output options

## Installation

```bash
# Clone or navigate to the project directory
cd W:\Projects\depivot

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

```bash
# Basic usage with ID columns
depivot data.xlsx --id-vars "ID,Name" --var-name "Month" --value-name "Sales"

# No ID columns - automatically adds row index
depivot data.xlsx --var-name "Month" --value-name "Sales"

# Process all sheets, output to specific file
depivot data.xlsx output.xlsx --id-vars "ID"

# Process only specific sheets
depivot data.xlsx --id-vars "ID" --sheet-names "Sales,Revenue"

# Skip certain sheets (e.g., metadata sheets)
depivot data.xlsx --id-vars "ID" --skip-sheets "Notes,Metadata"
```

## Usage

### Command Syntax

```bash
depivot [OPTIONS] INPUT_PATH [OUTPUT_PATH]
```

### Required Arguments

- `INPUT_PATH`: Path to Excel file or directory (required)

### Optional Arguments

- `OUTPUT_PATH`: Output file path (optional, defaults to `<input>_unpivoted.xlsx`)

### Data Transformation Options

- `--id-vars`, `-i`: Identifier columns to keep (comma-separated)
  - **Optional** - If not specified, a row index will be automatically added
  - Example: `--id-vars "ID,Name,Date"`

- `--value-vars`, `-v`: Columns to unpivot (comma-separated)
  - If not specified, all non-id columns will be unpivoted
  - Example: `--value-vars "Q1,Q2,Q3,Q4"`

- `--var-name`: Name for the variable column in output (default: "variable")
  - Example: `--var-name "Quarter"`

- `--value-name`: Name for the value column in output (default: "value")
  - Example: `--value-name "Sales"`

- `--index-name`: Name for auto-generated row index column (default: "Row")
  - Only used when `--id-vars` is not specified
  - Example: `--index-name "RowNumber"`

### Multi-Sheet Options

- `--sheet-names`, `-s`: Specific sheets to process (comma-separated)
  - Example: `--sheet-names "Sales,Revenue"`
  - Default: Process all sheets

- `--skip-sheets`: Sheet names to skip (comma-separated)
  - Example: `--skip-sheets "Metadata,Notes"`
  - Useful for excluding reference sheets

### Column Filtering

- `--include-cols`: Only include these columns (comma-separated)
- `--exclude-cols`, `-e`: Exclude these columns (comma-separated)
- `--drop-na`: Drop rows with NA values after unpivoting

### Row Filtering

- `--exclude-totals`: Exclude summary/total rows (e.g., "Grand Total", "Subtotal")
  - Automatically detects common summary row patterns
  - Applied to ID columns
- `--summary-patterns`: Custom patterns to identify summary rows (comma-separated)
  - Example: `--summary-patterns "Total,Sum,Aggregate"`
  - Case-insensitive matching

### Configuration Files

- `--config`, `-c`: Load parameters from YAML configuration file
  - Example: `--config settings.yaml`
  - CLI arguments override config file values
- `--save-config`: Save current parameters to YAML configuration file
  - Example: `--save-config settings.yaml`
  - Can be used standalone without processing files
  - Saves all transformation settings for reuse

### Batch Processing Options

- `--pattern`, `-p`: Glob pattern for finding files (default: "*.xlsx")
  - Example: `--pattern "sales_*.xlsx"`

- `--output-dir`, `-o`: Output directory for batch processing
  - Required when INPUT_PATH is a directory

- `--suffix`: Suffix for output filenames (default: "_unpivoted")
  - Example: `--suffix "_long"`

- `--recursive`, `-r`: Recursively search subdirectories

### SQL Server Upload Options

- `--sql-only`: Upload to SQL Server only (skip Excel file creation)
- `--excel-only`: Create Excel file only (default behavior)
- `--both`: Create both Excel file AND upload to SQL Server
- `--sql-connection-string`: SQL Server connection string
  - Example: `"Driver={ODBC Driver 18 for SQL Server};Server=SERVER;Database=DB;UID=user;PWD=pass;"`
- `--sql-table`: Target SQL Server table name
  - Example: `"[dbo].[Budget_Actuals]"`
- `--sql-mode`: Insert mode - `append` (default) or `replace` (truncate first)
- `--sql-l2-lookup-table`: Lookup table for L2_Proj mapping (default: `[dbo].[Intel_Site_Names]`)

### Validation Options

- `--no-quality-validation`: Skip data quality validation (validation runs by default if configured in YAML)
  - Template validation still runs if configured
  - Use when you need faster processing and trust data quality

### General Options

- `--overwrite`: Overwrite existing output files
- `--verbose`: Verbose output with detailed progress
- `--dry-run`: Preview what would be done without executing
- `--help`: Show help message
- `--version`: Show version

## Examples

### Single File Processing

```bash
# Basic depivot with ID columns
depivot sales.xlsx --id-vars "Region,Product"

# No ID columns - automatically adds row index
depivot data.xlsx --var-name "Month" --value-name "Sales"

# No ID columns with custom index name
depivot data.xlsx \
  --var-name "Month" \
  --value-name "Sales" \
  --index-name "RowNumber"

# Specify output file and column names
depivot sales.xlsx sales_long.xlsx \
  --id-vars "ID,Name" \
  --var-name "Month" \
  --value-name "Revenue"

# Process only specific value columns
depivot data.xlsx --id-vars "ID" \
  --value-vars "Jan,Feb,Mar,Apr" \
  --var-name "Month"

# Exclude certain columns from processing
depivot data.xlsx --id-vars "ID,Name" \
  --exclude-cols "Notes,Comments"
```

### Multi-Sheet Processing

```bash
# Process all sheets in a workbook
depivot workbook.xlsx --id-vars "ID,Name" --verbose

# Process only Sales and Revenue sheets
depivot workbook.xlsx --id-vars "ProductID" \
  --sheet-names "Sales,Revenue" \
  --var-name "Quarter"

# Skip metadata sheets
depivot workbook.xlsx --id-vars "ID" \
  --skip-sheets "Metadata,Notes,References"
```

### Batch Processing

```bash
# Process all Excel files in a directory
depivot ./data/ --id-vars "ID" --output-dir ./output/

# Process with custom pattern and suffix
depivot ./reports/ --id-vars "Region" \
  --pattern "sales_*.xlsx" \
  --output-dir ./processed/ \
  --suffix "_transformed"

# Recursive batch processing
depivot ./data/ --id-vars "ID,Date" \
  --output-dir ./output/ \
  --recursive \
  --verbose

# Batch process and skip certain sheets in all files
depivot ./data/ --id-vars "ID" \
  --output-dir ./output/ \
  --skip-sheets "Metadata"
```

### Row Filtering

```bash
# Exclude summary rows automatically
depivot data.xlsx --id-vars "Site,Category" \
  --exclude-totals

# Use custom summary patterns
depivot data.xlsx --id-vars "Site,Category" \
  --exclude-totals \
  --summary-patterns "Total,Sum,Subtotal,Aggregate"
```

### Configuration Files

```bash
# Save commonly used parameters to a config file
depivot test.xlsx output.xlsx \
  --id-vars "Site,Category" \
  --value-vars "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec" \
  --var-name "Month" \
  --value-name "Amount" \
  --header-row 2 \
  --exclude-totals \
  --save-config settings.yaml

# Load parameters from config file
depivot data.xlsx output.xlsx \
  --config settings.yaml

# Override specific parameters from config
depivot data.xlsx output.xlsx \
  --config settings.yaml \
  --var-name "Period"  # Overrides var-name from config
```

### SQL Server Upload

Upload depivoted data directly to SQL Server with automatic data transformation:

**Output Modes:**
- `--sql-only`: Upload to SQL Server only (skip Excel file creation)
- `--excel-only`: Create Excel file only (default behavior)
- `--both`: Create both Excel file AND upload to SQL Server

**SQL Options:**
- `--sql-connection-string`: SQL Server connection string
- `--sql-table`: Target table name (e.g., `[dbo].[TableName]`)
- `--sql-mode`: Insert mode - `append` (default) or `replace` (truncate first)
- `--sql-l2-lookup-table`: Lookup table for L2_Proj mapping (default: `[dbo].[Intel_Site_Names]`)

**Data Transformations:**
The SQL upload automatically transforms data to match the SQL Server schema:
- Month names (Jan, Feb, Mar) → Period numbers (1, 2, 3, ..., 12)
- ReleaseDate (YYYY-MM) → FiscalYear (extract year as integer)
- Site → L2_Proj (lookup from Intel_Site_Names table)
- DataType → Status column
- Actuals/Forecast classification based on `--forecast-start` parameter

```bash
# Upload to SQL Server only (no Excel file)
depivot data.xlsx dummy.xlsx \
  --id-vars "Site,Category" \
  --value-vars "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec" \
  --var-name "Month" \
  --value-name "Amount" \
  --sql-only \
  --sql-connection-string "Driver={ODBC Driver 18 for SQL Server};Server=SERVER;Database=DB;UID=user;PWD=pass;" \
  --sql-table "[dbo].[Budget_Actuals]"

# Create both Excel and upload to SQL
depivot data.xlsx output.xlsx \
  --config settings.yaml \
  --both \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[Budget_Actuals]" \
  --sql-mode append

# Replace existing data in SQL table
depivot data.xlsx output.xlsx \
  --config settings.yaml \
  --both \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[Budget_Actuals]" \
  --sql-mode replace

# Save SQL settings in config file for reuse
depivot test.xlsx output.xlsx \
  --id-vars "Site,Category" \
  --var-name "Month" \
  --value-name "Amount" \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[Budget_Actuals]" \
  --sql-mode append \
  --save-config sql_config.yaml

# Load SQL settings from config
depivot data.xlsx output.xlsx \
  --config sql_config.yaml \
  --both
```

**SQL Server Schema Requirements:**

The target SQL table should have the following columns:
- `L2_Proj` (varchar) - Mapped from lookup table
- `Site` (varchar) - Direct from source data
- `Category` (varchar) - Direct from source data
- `FiscalYear` (int) - Extracted from ReleaseDate
- `Period` (int) - Converted from month name (1-12)
- `Actuals` (float) - Value column
- `Status` (varchar) - DataType (Actual/Budget/Forecast)

**Prerequisites:**
- Install ODBC Driver 18 for SQL Server
- Install pyodbc: `pip install pyodbc>=5.0.0`
- Ensure network access to SQL Server
- Create lookup table `[dbo].[Intel_Site_Names]` with `[Site Name]` and `[L2_Proj]` columns

### Data Quality and Template Validation

The depivot tool includes two complementary validation systems to ensure data integrity and Excel file structure compliance:

#### Template Validation

Validates Excel file structure, sheet names, headers, and formats **before** data processing using a three-phase approach:

**Phase 1 - File Structure** (~50-100ms):
- Verify required sheets exist
- Validate sheet count within expected range

**Phase 2 - Sheet Template** (~20-50ms per sheet):
- Check header row content and position
- Detect problematic merged cells
- Validate cell formats (numeric columns)

**Phase 3 - DataFrame** (~10-20ms per sheet):
- Ensure required columns present
- Validate column ordering

**Configuration Example:**

```yaml
# config.yaml
template_validation:
  enabled: true

  file_structure:
    - check: expected_sheets
      enabled: true
      severity: error
      params:
        required_sheets: ["Workings - Actuals & Budgets"]
        allow_extra_sheets: true
      message: "Required sheet not found"

  sheet_template:
    - check: header_row
      enabled: true
      severity: error
      params:
        row_number: 3  # 1-indexed (Excel row 3)
        expected_columns: ["Site", "Category", "Jan", "Feb", "Mar"]
        exact_order: false
        allow_extra_columns: true
      message: "Header row mismatch in sheet '{sheet}'"

    - check: merged_cells
      enabled: true
      severity: warning
      params:
        allowed: false
      message: "Merged cells detected in '{sheet}': {ranges}"

  dataframe_template:
    - check: required_columns
      enabled: true
      severity: error
      params:
        columns: ["Site", "Category"]
      message: "Required columns missing in '{sheet}': {missing}"

  settings:
    stop_on_error: true
    verbose: false
```

#### Data Quality Validation

Validates data integrity before and after depivoting with 10 configurable rules:

**Pre-Processing Rules** (run before depivoting):
1. **check_null_values** - Detect excessive NULL/missing values
2. **check_duplicates** - Find duplicate rows
3. **check_column_types** - Validate expected data types
4. **check_value_ranges** - Check values within min/max ranges
5. **check_required_columns** - Ensure required columns exist and non-empty

**Post-Processing Rules** (run after depivoting):
1. **check_row_count** - Validate row count matches expectations
2. **check_numeric_conversion** - Track NULL values in depivoted data
3. **check_outliers** - Detect statistical outliers (z-score or IQR)
4. **check_data_completeness** - Find missing dimension combinations
5. **check_totals_match** - Verify totals match between source and processed data

**Configuration Example:**

```yaml
# config.yaml
validation_rules:
  enabled: true

  pre_processing:
    - rule: check_null_values
      enabled: true
      severity: warning
      params:
        columns: ["Site", "Category"]
        threshold: 0.05  # Allow up to 5% NULLs
      message: "Excessive NULL values in {column}: {percent}%"

    - rule: check_duplicates
      enabled: true
      severity: error
      params:
        key_columns: ["Site", "Category"]
      message: "Duplicate rows detected: {count} duplicates found"

    - rule: check_required_columns
      enabled: true
      severity: error
      params:
        columns: ["Site", "Category"]
        allow_all_null: false
      message: "Required column {column} missing or empty"

  post_processing:
    - rule: check_row_count
      enabled: true
      severity: error
      params:
        min_ratio: 0.95  # At least 95% of expected rows
        max_ratio: 1.05  # At most 105% of expected rows
      message: "Row count mismatch: expected {expected}, got {actual}"

    - rule: check_totals_match
      enabled: true
      severity: error
      params:
        tolerance: 0.01  # Absolute difference tolerance
      message: "Totals mismatch: source={source_total}, processed={processed_total}"

  validation_settings:
    stop_on_error: true
    max_warnings_display: 20
    verbose_rules: false
```

**Using Validation:**

```bash
# Run with validation configured in YAML
depivot data.xlsx output.xlsx --config config.yaml --verbose

# Disable data quality validation (template validation still runs)
depivot data.xlsx output.xlsx --config config.yaml --no-quality-validation

# Validation output shows results for each phase
# Validating template structure...
# Data Quality - PRE-Sheet1 Results:
#   Passed: 3
#   Warnings: 0
#   Errors: 0
# Data Quality - POST-Sheet1 Results:
#   Passed: 4
#   Warnings: 0
#   Errors: 0
```

**Severity Levels:**
- `error`: Stop processing immediately
- `warning`: Log warning but continue
- `info`: Informational only

**Performance Impact:**
- Template validation: <200ms overhead per file
- Data quality validation: <100ms overhead per sheet
- Both systems add minimal processing time while ensuring data integrity

For detailed validation configuration, see `W:\Intel Data\DATA_QUALITY_VALIDATION_GUIDE.md`.

### Advanced Usage

```bash
# Drop NA values after unpivoting
depivot data.xlsx --id-vars "ID" --drop-na

# Dry run to preview without processing
depivot ./data/ --id-vars "ID" \
  --output-dir ./output/ \
  --dry-run

# Overwrite existing files
depivot data.xlsx output.xlsx \
  --id-vars "ID" \
  --overwrite

# Verbose output for debugging
depivot data.xlsx --id-vars "ID,Name" \
  --verbose
```

## How It Works

1. **Sheet Discovery**: Identifies all sheets in the workbook (or filters by name)
2. **Data Loading**: Reads each sheet into a pandas DataFrame
3. **Column Validation**: Verifies that id_vars exist in each sheet
4. **Column Resolution**: Determines which columns to unpivot (value_vars)
5. **Depivoting**: Uses pandas `melt()` to transform wide to long format
6. **Output Writing**: Writes all depivoted sheets to output workbook

## Multi-Sheet Behavior

- By default, ALL sheets in a workbook are processed
- Each sheet is depivoted with the same settings (id_vars, value_vars, etc.)
- Output maintains separate sheets with the same names as input
- Use `--sheet-names` to process only specific sheets
- Use `--skip-sheets` to exclude certain sheets (like metadata)

## Requirements

- Python 3.9+
- pandas >= 2.0.0
- openpyxl >= 3.1.0
- click >= 8.1.0
- rich >= 13.0.0
- pyyaml >= 6.0.0
- pyodbc >= 5.0.0 (for SQL Server upload)

## Project Structure

```
depivot/
├── src/
│   └── depivot/
│       ├── __init__.py            # Package initialization
│       ├── __main__.py            # Enable python -m depivot
│       ├── cli.py                 # Click CLI interface (94% coverage)
│       ├── core.py                # Core depivoting logic (87% coverage)
│       ├── config.py              # Configuration file handling (100% coverage)
│       ├── sql_upload.py          # SQL Server upload functionality (92% coverage)
│       ├── data_quality.py        # Data quality validation engine (95% coverage)
│       ├── quality_rules.py       # 10 data quality validation rules (93% coverage)
│       ├── template_validators.py # Excel template validation (96% coverage)
│       ├── validators.py          # Input validation (100% coverage)
│       ├── exceptions.py          # Custom exceptions (100% coverage)
│       └── utils.py               # Helper utilities (100% coverage)
├── tests/                         # Comprehensive test suite (323 tests, 92% coverage)
│   ├── test_cli.py                # CLI tests (37 tests)
│   ├── test_core.py               # Core logic tests (57 tests)
│   ├── test_config.py             # Configuration tests (19 tests)
│   ├── test_sql_upload.py         # SQL upload tests (33 tests)
│   ├── test_data_quality.py       # Data quality tests (36 tests)
│   ├── test_quality_rules.py      # Quality rules tests (44 tests)
│   ├── test_template_validators.py # Template validation tests (41 tests)
│   ├── test_validators.py         # Input validation tests (23 tests)
│   ├── test_utils.py              # Utilities tests (36 tests)
│   ├── test_integration.py        # Integration tests (3 tests)
│   └── conftest.py                # Test fixtures and configuration
├── examples/                      # Example files and documentation
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Dependencies
├── README.md                      # This file
└── DEVELOPMENT.md                 # Technical development documentation
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run as module
python -m depivot --help

# Run from source
python src/depivot/cli.py --help
```

### Testing

The project has a comprehensive test suite with **92% overall code coverage**:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src/depivot --cov-report=term

# Run tests with HTML coverage report
pytest --cov=src/depivot --cov-report=html

# Run specific test file
pytest tests/test_core.py -v

# Run tests matching a pattern
pytest -k "test_depivot" -v
```

**Test Coverage by Module:**
- cli.py: 94% (37 tests)
- core.py: 87% (57 tests)
- config.py: 100% (19 tests)
- sql_upload.py: 92% (33 tests)
- data_quality.py: 95% (36 tests)
- quality_rules.py: 93% (44 tests)
- template_validators.py: 96% (41 tests)
- validators.py: 100% (23 tests)
- utils.py: 100% (36 tests)
- exceptions.py: 100%

**Total:** 323 tests, 92% coverage across all platforms (Ubuntu, Windows, macOS) and Python versions (3.9-3.12)

## Error Handling

The tool provides clear error messages for common issues:

- File not found
- Invalid Excel format
- Missing columns in sheets
- Sheet name not found
- Overwrite conflicts
- Column specification errors
- Template validation errors (missing sheets, header mismatches, merged cells)
- Data quality validation errors (duplicates, NULL values, row count mismatches)

Use `--verbose` for detailed error information and validation results.

## License

MIT License

## Author

depivot

## Version

0.1.0
