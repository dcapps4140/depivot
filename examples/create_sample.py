"""Create a sample multi-sheet Excel file for demonstration."""

import pandas as pd
from pathlib import Path

# Sample data for Sales sheet
sales_data = {
    "ID": [1, 2, 3, 4],
    "Product": ["Widget A", "Widget B", "Widget C", "Widget D"],
    "Region": ["North", "South", "East", "West"],
    "Jan": [100, 150, 200, 175],
    "Feb": [120, 160, 210, 185],
    "Mar": [140, 155, 220, 190],
    "Apr": [130, 170, 215, 195],
}

# Sample data for Revenue sheet
revenue_data = {
    "ProductID": [1, 2, 3, 4],
    "Name": ["Widget A", "Widget B", "Widget C", "Widget D"],
    "Q1": [15000, 22500, 30000, 26250],
    "Q2": [16500, 24000, 31500, 27750],
    "Q3": [17250, 23250, 32250, 28500],
    "Q4": [18000, 25500, 33000, 29250],
}

# Sample metadata sheet (to demonstrate skip-sheets)
metadata = {
    "Info": ["Created", "Version", "Description"],
    "Value": [
        "2025-12-31",
        "1.0",
        "Sample data for depivot demonstration",
    ],
}

# Create output directory
output_dir = Path(__file__).parent
output_file = output_dir / "sample_input.xlsx"

# Create Excel file with multiple sheets
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    pd.DataFrame(sales_data).to_excel(writer, sheet_name="Sales", index=False)
    pd.DataFrame(revenue_data).to_excel(writer, sheet_name="Revenue", index=False)
    pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)

print(f"Created sample file: {output_file}")
print("\nSheets:")
print("  - Sales: Monthly sales data (wide format)")
print("  - Revenue: Quarterly revenue data (wide format)")
print("  - Metadata: Information sheet (typically skipped)")
print("\nTry running:")
print(f'  depivot "{output_file}" --id-vars "ID,Product,Region" --var-name "Month" --verbose')
print(f'  depivot "{output_file}" --id-vars "ID,Product,Region" --skip-sheets "Metadata"')
