# Depivot Examples

This directory contains example files demonstrating the depivot tool.

## Sample Input File

`sample_input.xlsx` contains three worksheets:

### 1. Sales Sheet (Wide Format)
```
ID | Product  | Region | Jan | Feb | Mar | Apr
1  | Widget A | North  | 100 | 120 | 140 | 130
2  | Widget B | South  | 150 | 160 | 155 | 170
3  | Widget C | East   | 200 | 210 | 220 | 215
4  | Widget D | West   | 175 | 185 | 190 | 195
```

### 2. Revenue Sheet (Wide Format)
```
ProductID | Name     | Q1    | Q2    | Q3    | Q4
1         | Widget A | 15000 | 16500 | 17250 | 18000
2         | Widget B | 22500 | 24000 | 23250 | 25500
3         | Widget C | 30000 | 31500 | 32250 | 33000
4         | Widget D | 26250 | 27750 | 28500 | 29250
```

### 3. Metadata Sheet
Information sheet (typically skipped during processing)

## Example Commands

### Process All Sheets
```bash
depivot sample_input.xlsx --id-vars "ID,Product,Region" --var-name "Month" --value-name "Sales"
```

Output creates a file with 2 depivoted sheets (Sales and Revenue transformed to long format).

### Skip Metadata Sheet
```bash
depivot sample_input.xlsx --id-vars "ID,Product,Region" --skip-sheets "Metadata" --verbose
```

### Process Only Sales Sheet
```bash
depivot sample_input.xlsx --id-vars "ID,Product,Region" --sheet-names "Sales" --var-name "Month"
```

### Expected Output for Sales Sheet

After depivoting the Sales sheet:
```
ID | Product  | Region | Month | Sales
1  | Widget A | North  | Jan   | 100
1  | Widget A | North  | Feb   | 120
1  | Widget A | North  | Mar   | 140
1  | Widget A | North  | Apr   | 130
2  | Widget B | South  | Jan   | 150
2  | Widget B | South  | Feb   | 160
...
```

## Regenerating Sample File

To recreate the sample file:
```bash
python create_sample.py
```

## Configuration Files

The `examples/` directory includes ready-to-use YAML configuration files:

### `basic_config.yaml`
Basic depivoting configuration without SQL upload or validation.

**Usage:**
```bash
depivot input.xlsx output.xlsx --config examples/basic_config.yaml
```

**Includes:**
- ID columns, variable/value names
- Sheet processing options
- Row filtering settings
- Custom column additions

### `sql_upload_config.yaml`
Configuration for uploading depivoted data to SQL Server.

**Usage:**
```bash
depivot input.xlsx output.xlsx --config examples/sql_upload_config.yaml --both
```

**Includes:**
- SQL Server connection settings
- Target table: `Intel_Project.dbo.FY25_Budget_Actuals_DIBS`
- Upload mode (append/replace)
- L2_Proj lookup table configuration

**Important:** Update the connection string with your actual credentials before use!

### `validation_config.yaml`
Configuration with template and data quality validation enabled.

**Usage:**
```bash
depivot input.xlsx output.xlsx --config examples/validation_config.yaml
```

**Includes:**
- Template validation (expected headers, column order)
- Data quality rules (nulls, duplicates, ranges, types)
- Validation severity levels (error/warning/info)
- Validation report generation

## Saving Custom Configurations

You can save your command-line options to a config file:

```bash
depivot input.xlsx output.xlsx \
  --id-vars "Site,Category" \
  --var-name "Month" \
  --value-name "Amount" \
  --sql-connection-string "Driver={...};" \
  --sql-table "[dbo].[FY25_Budget_Actuals_DIBS]" \
  --save-config my_config.yaml
```

This creates `my_config.yaml` with all your settings for future use.
