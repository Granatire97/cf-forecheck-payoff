from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "flames_data_challenge_warehouse.duckdb"
RAW_PATH = ROOT / "data" / "raw" / "olympic_womens_dataset.csv"