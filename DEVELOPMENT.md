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
│   ├── cli.py                # Click CLI interface - entry point (94% coverage)
│   ├── core.py               # Core business logic (87% coverage)
│   ├── config.py             # Configuration file handling (100% coverage)
│   ├── sql_upload.py         # SQL Server upload functionality (92% coverage)
│   ├── data_quality.py       # Data quality validation engine (95% coverage)
│   ├── quality_rules.py      # 10 data quality validation rules (93% coverage)
│   ├── template_validators.py # Excel template validation (96% coverage)
│   ├── validators.py         # Input validation functions (100% coverage)
│   ├── exceptions.py         # Custom exception hierarchy (100% coverage)
│   └── utils.py              # Helper utilities (100% coverage)
├── tests/                    # Comprehensive test suite (323 tests, 92% coverage)
│   ├── test_cli.py           # CLI tests (37 tests)
│   ├── test_core.py          # Core logic tests (57 tests)
│   ├── test_config.py        # Configuration tests (19 tests)
│   ├── test_sql_upload.py    # SQL upload tests (33 tests)
│   ├── test_data_quality.py  # Data quality tests (36 tests)
│   ├── test_quality_rules.py # Quality rules tests (44 tests)
│   ├── test_template_validators.py # Template validation tests (41 tests)
│   ├── test_validators.py    # Input validation tests (23 tests)
│   ├── test_utils.py         # Utilities tests (36 tests)
│   ├── test_integration.py   # Integration tests (3 tests)
│   └── conftest.py           # Test fixtures and configuration
├── examples/                 # Example files and documentation
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
- `pyyaml>=6.0.0` - YAML configuration file support
- `pyodbc>=5.0.0` - SQL Server connectivity via ODBC driver

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

### 7. Row Filtering

**Purpose**: Automatically exclude summary/total rows (e.g., "Grand Total", "Subtotal") from processing to prevent data duplication and validation mismatches.

**Implementation** (`utils.py:is_summary_row()`):
```python
def is_summary_row(row_data: dict, id_cols: List[str], summary_patterns: Optional[List[str]] = None) -> bool:
    """Check if a row appears to be a summary/total row."""
    if summary_patterns is None:
        # Default summary patterns
        summary_patterns = [
            "grand total", "total", "subtotal", "sub-total",
            "sub total", "sum", "summary"
        ]

    # Check each ID column for summary patterns
    for col in id_cols:
        if col in row_data:
            value = str(row_data[col]).lower().strip()
            for pattern in summary_patterns:
                if pattern in value:
                    return True
    return False
```

**Usage in core.py**:
```python
# Filter out summary/total rows if requested
if exclude_totals and id_vars:
    initial_row_count = len(df)
    mask = df.apply(
        lambda row: not is_summary_row(row.to_dict(), id_vars, summary_patterns),
        axis=1
    )
    df = df[mask].copy()
    filtered_count = initial_row_count - len(df)

    if filtered_count > 0 and verbose:
        console.print(f"    [yellow]Filtered {filtered_count} summary row(s)[/yellow]")
```

**Key Points**:
- Case-insensitive pattern matching
- Checks all ID columns for summary indicators
- Custom patterns supported via `--summary-patterns`
- Validation data stored AFTER filtering to prevent mismatches

### 8. Configuration File Support

**Purpose**: Save commonly used parameter sets to avoid repetitive long command lines.

**Format**: YAML (human-readable, supports comments)

**Implementation** (`config.py`):
```python
def load_config(config_file: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config or {}

def save_config(config_file: Path, config: Dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def get_config_params(options: Dict[str, Any]) -> Dict[str, Any]:
    """Extract saveable parameters (excludes runtime flags like verbose)."""
    saveable_params = [
        "id_vars", "value_vars", "var_name", "value_name",
        "include_cols", "exclude_cols", "sheet_names", "skip_sheets",
        "header_row", "drop_na", "index_col_name", "data_type_col",
        "data_type_override", "forecast_start", "combine_sheets",
        "output_sheet_name", "exclude_totals", "summary_patterns",
    ]
    # Convert lists to comma-separated strings for readability
    # Return only non-None values
```

**CLI Integration**:
- `--config <file>`: Load parameters from YAML file
- `--save-config <file>`: Save current parameters to YAML file
- CLI arguments override config file values
- Can save config without processing files

**Example Config File** (`intel_actuals.yaml`):
```yaml
id_vars: Site,Category
value_vars: Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec
var_name: Month
value_name: Amount
sheet_names: Workings - Actuals & Budgets
header_row: 2
drop_na: false
index_col_name: Row
data_type_col: DataType
data_type_override: Actual
forecast_start: March
combine_sheets: false
output_sheet_name: Data
exclude_totals: true
sql_connection_string: Driver={ODBC Driver 18 for SQL Server};Server=SERVER;Database=DB;UID=user;PWD=pass;
sql_table: '[dbo].[Budget_Actuals]'
sql_mode: append
sql_l2_lookup_table: '[dbo].[Intel_Site_Names]'
```

### 9. SQL Server Upload

**Purpose**: Upload depivoted data directly to SQL Server database, eliminating manual Excel→SQL import steps and enabling automated data pipelines.

**Architecture**:
- `sql_upload.py` module contains all SQL Server operations
- Automatic data transformation to match SQL Server schema
- Bulk insert using parameterized queries for performance and security
- L2_Proj lookup via SQL query before upload (pre-fetch strategy)

**Output Modes**:
- `--sql-only`: Upload to SQL only, skip Excel file creation
- `--excel-only`: Create Excel only (default, backward compatible)
- `--both`: Create both Excel file AND upload to SQL

**Data Transformations** (`transform_dataframe_for_sql()`):

| Depivot Output | → | SQL Server Column | Transformation |
|---|---|---|---|
| Site | → | Site | Direct copy |
| Category | → | Category | Direct copy |
| Month (Jan, Feb, Mar) | → | Period (1, 2, 3) | `convert_month_to_period()` |
| Amount | → | Actuals | Direct copy (renamed) |
| DataType | → | Status | Direct copy (renamed) |
| ReleaseDate (2025-02) | → | FiscalYear (2025) | `extract_fiscal_year()` - extract year as int |
| Site (lookup) | → | L2_Proj | `fetch_l2_proj_mapping()` - lookup from Intel_Site_Names |

**Month to Period Mapping**:
```python
MONTH_TO_PERIOD = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    # ... all months 1-12
}
```

**L2_Proj Lookup Strategy**:
- Pre-fetch mapping dictionary from lookup table before upload
- SQL Query: `SELECT DISTINCT [Site Name], [L2_Proj] FROM [dbo].[Intel_Site_Names]`
- Map via pandas: `df['L2_Proj'] = df['Site'].map(l2_proj_mapping)`
- More efficient than JOIN for bulk uploads
- Warns about missing mappings but continues with NULL

**Bulk Insert Implementation**:
```python
# Parameterized INSERT statement
insert_sql = """
    INSERT INTO {table_name}
    (L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

# Bulk insert with executemany() for performance
rows = df[columns].values.tolist()
cursor.executemany(insert_sql, rows)
conn.commit()
```

**SQL Insert Modes**:
- `append` (default): Add rows to existing data (`INSERT INTO`)
- `replace`: Truncate table first (`TRUNCATE TABLE` then `INSERT INTO`)

**NaN/NULL Handling**:
- Converts pandas NaN to Python None before upload
- SQL Server receives NULL values correctly
- Critical for numeric columns with missing data

**Error Handling**:
- Connection validation before processing
- Clear error messages for:
  - ODBC driver not found
  - Connection failures
  - Table doesn't exist
  - Invalid data types
  - Missing required columns

**SQL Server Schema Requirements**:
```sql
CREATE TABLE [dbo].[FY25_Budget_Actuals_DIBS] (
    [PK_IDX] INT IDENTITY(1,1) PRIMARY KEY,
    [L2_Proj] VARCHAR(50),
    [Site] VARCHAR(100) NOT NULL,
    [Category] VARCHAR(100) NOT NULL,
    [FiscalYear] INT,
    [Period] INT,
    [Actuals] FLOAT,
    [Status] VARCHAR(20)
)

-- Lookup table
CREATE TABLE [dbo].[Intel_Site_Names] (
    [Site Name] VARCHAR(100) PRIMARY KEY,
    [L2_Proj] VARCHAR(50) NOT NULL
)
```

**CLI Options**:
- `--sql-connection-string`: Connection string (can be saved in config file)
- `--sql-table`: Target table name (e.g., `[dbo].[Budget_Actuals]`)
- `--sql-mode`: `append` or `replace`
- `--sql-l2-lookup-table`: Lookup table name (default: `[dbo].[Intel_Site_Names]`)

**Key Implementation Details**:
1. **Connection String Format**: Uses ODBC Driver 18 with explicit encrypt/trust settings
   ```
   Driver={ODBC Driver 18 for SQL Server};Server=SERVER;Database=DB;UID=user;PWD=pass;Encrypt=no;TrustServerCertificate=yes;
   ```

2. **Data Quality**: Automatically filters out:
   - Rows where Site or Category is NULL
   - Rows containing "total" in Site or Category (summary rows)
   - Budget rows where ALL month values are NULL

3. **Validation**: SQL upload happens AFTER Excel validation, so validation report is still generated even in `--sql-only` mode (stored in memory, not written to disk)

4. **Performance**: Processes ~3000 rows in <5 seconds including transformations and bulk insert

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
  --exclude-totals \
  --verbose
```

### Save Configuration File for Repeated Use
```bash
# Save configuration for Actuals processing
depivot test.xlsx output.xlsx \
  --id-vars "Site,Category" \
  --value-vars "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec" \
  --var-name "Month" \
  --value-name "Amount" \
  --forecast-start "March" \
  --data-type-override "Actual" \
  --sheet-names "Workings - Actuals & Budgets" \
  --header-row 2 \
  --exclude-totals \
  --save-config "W:\Intel Data\intel_actuals.yaml"

# Use saved configuration (much shorter command!)
depivot "W:\Intel Data\2025_02_All Sites.xlsx" \
  "W:\Intel Data\2025_02_Actuals.xlsx" \
  --config "W:\Intel Data\intel_actuals.yaml" \
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

### Upload to SQL Server

```bash
# Upload depivoted data to SQL Server (both Excel and SQL)
depivot "W:\Intel Data\2025_02_All Sites.xlsx" \
  "W:\Intel Data\2025_02_Actuals.xlsx" \
  --config "W:\Intel Data\intel_actuals.yaml" \
  --both \
  --sql-connection-string "Driver={ODBC Driver 18 for SQL Server};Server=NAILDC-SRV1;Database=Intel_Project;UID=sa;PWD=sqlserver1!;Encrypt=no;TrustServerCertificate=yes;" \
  --sql-table "[dbo].[FY25_Budget_Actuals_DIBS]" \
  --sql-mode replace \
  --verbose

# SQL upload only (no Excel file)
depivot "W:\Intel Data\2025_02_All Sites.xlsx" \
  dummy.xlsx \
  --config "W:\Intel Data\intel_actuals.yaml" \
  --sql-only \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[FY25_Budget_Actuals_DIBS]"

# Save SQL connection in config file for reuse
depivot test.xlsx output.xlsx \
  --id-vars "Site,Category" \
  --var-name "Month" \
  --value-name "Amount" \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[FY25_Budget_Actuals_DIBS]" \
  --save-config sql_config.yaml
```

**Result**:
- Automatic transformations: Month→Period, ReleaseDate→FiscalYear, Site→L2_Proj
- Status classification: Actual (Jan-Feb), Forecast (Mar-Dec)
- 160 rows → 1,920 rows uploaded to SQL Server
- L2_Proj mapping applied from Intel_Site_Names table
- Summary rows and NULL-only Budget rows automatically filtered

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

### Phase 7: Row Filtering & Configuration Files
- **Row filtering**: Automatically exclude summary/total rows
  - `--exclude-totals` flag
  - `--summary-patterns` for custom patterns
  - Default patterns: "grand total", "total", "subtotal", "sum", "summary"
  - is_summary_row() utility function
  - Validation data stored after filtering to prevent mismatches
- **Configuration file support**: Save and load parameter sets
  - Added PyYAML dependency
  - config.py module with load/save/get functions
  - `--config` to load settings from YAML file
  - `--save-config` to save current parameters
  - CLI arguments override config values
  - Standalone save mode (no file processing required)

### Phase 8: SQL Server Upload Integration
- **Direct SQL Server upload**: Eliminate manual Excel→SQL import steps
  - Added pyodbc dependency (>=5.0.0)
  - sql_upload.py module with all database operations
  - DatabaseError exception added to exceptions.py
  - Output modes: `--sql-only`, `--excel-only`, `--both`
  - Insert modes: `append` (default) or `replace` (truncate first)
- **Automatic data transformation**:
  - Month names → Period numbers (Jan=1, Dec=12)
  - ReleaseDate → FiscalYear (extract year as integer)
  - Site → L2_Proj (lookup from Intel_Site_Names table)
  - DataType → Status column rename
  - Pre-fetch L2_Proj mapping for efficient bulk upload
- **Bulk insert optimization**: Parameterized executemany() for performance
- **NaN/NULL handling**: Proper conversion of pandas NaN to SQL NULL
- **Data quality filters**: Automatic exclusion of:
  - Summary rows (Grand Total, etc.)
  - Budget rows with all NULL months
  - Rows with NULL Site or Category
- **Configuration support**: SQL connection string and parameters saveable in YAML
- **Tested with production data**: Successfully processed 3072 rows (Actuals, Forecast, Budget)

### Phase 9: Validation Systems
- **Template validation**: 3-phase Excel file structure verification
  - template_validators.py module (96% coverage)
  - Phase 1: File structure validation (sheets existence, count)
  - Phase 2: Sheet template validation (headers, merged cells, formats)
  - Phase 3: DataFrame validation (required columns, ordering)
  - YAML configuration support with severity levels (error/warning/info)
  - Configurable stop-on-error behavior
  - Minimal performance overhead (<200ms per file)
- **Data quality validation**: Comprehensive pre/post-processing checks
  - data_quality.py validation engine (95% coverage)
  - quality_rules.py with 10 configurable rules (93% coverage)
  - Pre-processing rules: null values, duplicates, column types, value ranges, required columns
  - Post-processing rules: row count, numeric conversion, outliers, completeness, totals matching
  - YAML configuration with rule-specific parameters
  - Severity levels and custom validation messages
  - --no-quality-validation flag for faster processing when needed

### Phase 10: Comprehensive Test Suite & CI/CD
- **Automated testing infrastructure**: 323 tests with 92% code coverage
  - test_cli.py (37 tests, 94% coverage) - CLI interface and argument parsing
  - test_core.py (57 tests, 87% coverage) - Core depivoting logic
  - test_config.py (19 tests, 100% coverage) - Configuration file handling
  - test_sql_upload.py (33 tests, 92% coverage) - SQL Server operations
  - test_data_quality.py (36 tests, 95% coverage) - Data quality engine
  - test_quality_rules.py (44 tests, 93% coverage) - All 10 validation rules
  - test_template_validators.py (41 tests, 96% coverage) - Template validation
  - test_validators.py (23 tests, 100% coverage) - Input validation
  - test_utils.py (36 tests, 100% coverage) - Utility functions
  - test_integration.py (3 tests) - End-to-end workflows
  - conftest.py with reusable test fixtures
- **Continuous Integration**: GitHub Actions CI/CD pipeline
  - Multi-platform testing: Ubuntu, Windows, macOS
  - Multi-version testing: Python 3.9, 3.10, 3.11, 3.12
  - Automatic test execution on every commit and pull request
  - Cross-platform compatibility verification
  - Prevents regressions and ensures code quality

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

### Automated Test Suite

The project has a comprehensive automated test suite with **92% overall code coverage** across **323 tests**:

**Test Coverage by Module:**
- cli.py: 94% (37 tests) - Command-line interface, argument parsing, workflow orchestration
- core.py: 87% (57 tests) - Core depivoting logic, multi-file processing, validation
- config.py: 100% (19 tests) - Configuration file handling (YAML save/load)
- sql_upload.py: 92% (33 tests) - SQL Server upload, data transformations, bulk insert
- data_quality.py: 95% (36 tests) - Data quality validation engine
- quality_rules.py: 93% (44 tests) - 10 data quality validation rules
- template_validators.py: 96% (41 tests) - Excel template validation (3-phase approach)
- validators.py: 100% (23 tests) - Input validation functions
- utils.py: 100% (36 tests) - Helper utilities (file discovery, parsing, date extraction)
- exceptions.py: 100% - Custom exception hierarchy
- integration tests: 3 tests - End-to-end workflow validation

**Running Tests:**
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src/depivot --cov-report=term-missing

# Run tests with HTML coverage report
pytest --cov=src/depivot --cov-report=html

# Run specific test module
pytest tests/test_core.py -v

# Run tests matching a pattern
pytest -k "test_depivot_multi_file" -v
```

**Continuous Integration:**
- All tests run automatically on GitHub Actions for every commit
- Tests run across multiple platforms: Ubuntu, Windows, macOS
- Tests run across Python versions: 3.9, 3.10, 3.11, 3.12
- CI ensures cross-platform compatibility and prevents regressions

### Manual Testing Checklist
- [x] Single file, single sheet
- [x] Single file, multiple sheets
- [x] Wildcard with multiple files
- [x] --combine-sheets flag
- [x] --forecast-start logic
- [x] Decimal preservation
- [x] Validation report accuracy
- [x] Release date extraction
- [x] Edge cases: blank rows, summary rows, NaN values
- [x] SQL Server upload and transformations
- [x] Template validation (3-phase)
- [x] Data quality validation (pre/post-processing)

### Test Data
- Automated tests use synthetic test data generated in fixtures (see `tests/conftest.py`)
- Integration tests use realistic Excel structures
- Manual testing uses actual Intel data files from `W:\Intel Data\`
- Files: `2025_02_All Sites EAC Budget vs Actuals (Forecast Updates).xlsx`
- Expected output: 161 rows → 1,932 rows per sheet per file

## Future Enhancements

### Completed Improvements
1. ✅ **Row filtering** - exclude summary rows like "Grand Total" automatically (Phase 7)
2. ✅ **Configuration files** - save commonly used parameter sets (Phase 7)
3. ✅ **SQL Server direct upload** - upload depivoted data directly to SQL Server (Phase 8)
4. ✅ **Data quality validation** - comprehensive pre/post-processing data checks with 10 configurable rules (Phase 9)
5. ✅ **Excel template validation** - verify input files match expected structure with 3-phase validation approach (Phase 9)
6. ✅ **Comprehensive test suite** - 323 automated tests with 92% code coverage across all platforms (Phase 10)
7. ✅ **Continuous Integration** - GitHub Actions CI/CD pipeline testing on Ubuntu, Windows, macOS with Python 3.9-3.12

### Potential Improvements
1. **Parallel processing** - process multiple files concurrently for better performance
2. **Incremental updates** - only process new/changed files based on timestamps or checksums
3. **Other database support** - PostgreSQL, MySQL via SQLAlchemy abstraction
4. **Dual-dataset processing** - automatically detect and process side-by-side datasets (Actuals + Budget) in single pass
5. **Advanced anomaly detection** - ML-based outlier detection beyond basic statistical methods
6. **Web interface** - Flask/FastAPI web UI for non-technical users
7. **Scheduled processing** - Built-in scheduler for automated recurring data processing

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

**Last Updated**: January 6, 2026
**Version**: 0.1.0
**Python Version**: 3.9+
**Test Coverage**: 92% (323 tests)
