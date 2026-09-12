import pandas as pd
from backend.app.tools.data_loader import load_from_file

# Create a sample CSV
df = pd.DataFrame({
    "customer_id": [1, 2, 3],
    "age": [25, 30, 35],
    "city": ["NY", "SF", "LA"]
})
df.to_csv("sample.csv", index=False)

# Test loader
res = load_from_file("sample.csv")
print(f"Loaded dataset: {res.source_name}, Rows: {res.row_count}, Cols: {res.column_count}")
