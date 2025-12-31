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

## Project Structure

```
depivot/
├── src/
│   └── depivot/
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # Enable python -m depivot
│       ├── cli.py            # Click CLI interface
│       ├── core.py           # Core depivoting logic
│       ├── config.py         # Configuration file handling
│       ├── validators.py     # Input validation
│       ├── exceptions.py     # Custom exceptions
│       └── utils.py          # Helper utilities
├── examples/                 # Example files
├── pyproject.toml           # Project configuration
├── requirements.txt         # Dependencies
└── README.md               # This file
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

## Error Handling

The tool provides clear error messages for common issues:

- File not found
- Invalid Excel format
- Missing columns in sheets
- Sheet name not found
- Overwrite conflicts
- Column specification errors

Use `--verbose` for detailed error information.

## License

MIT License

## Author

depivot

## Version

0.1.0
