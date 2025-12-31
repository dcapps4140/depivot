"""Create a sample Excel file without ID columns."""

import pandas as pd
from pathlib import Path

# Sample data without ID columns - just month columns
data = {
    "Jan": [100, 150, 200],
    "Feb": [120, 160, 210],
    "Mar": [140, 155, 220],
    "Apr": [130, 170, 215],
}

# Create output file
output_dir = Path(__file__).parent
output_file = output_dir / "no_id_sample.xlsx"

# Create Excel file
pd.DataFrame(data).to_excel(output_file, index=False)

print(f"Created sample file: {output_file}")
print("\nData (no ID columns):")
print(pd.DataFrame(data))
print("\nTry running:")
print(f'  depivot "{output_file}" --var-name "Month" --value-name "Sales" --verbose')
