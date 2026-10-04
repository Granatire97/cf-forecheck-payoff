import pandas as pd
from pathlib import Path

for f in Path("data/raw").glob("*.csv"):
    df = pd.read_csv(f)
    print(f"\n=== {f.name}: {len(df):,} rows ===")
    print(df.columns.tolist())
    print(df["Event"].value_counts())
    print(df[["X Coordinate", "Y Coordinate"]].describe().loc[["min", "max"]])
    print(df["Clock"].head(3).tolist())