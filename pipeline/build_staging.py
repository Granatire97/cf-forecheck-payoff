import duckdb
from pathlib import Path
from pipeline.config import DB_PATH, RAW_PATH

CSV_SOURCES = {
    RAW_PATH: "staging.events"
    }

def load_csv_staging(db_path: Path = DB_PATH) -> None:
    """
    Load each raw CSV into its staging table, exactly as-is. Added event_id for file order
    """

    con = duckdb.connect(str(db_path))
    try:
        for csv_path, table in CSV_SOURCES.items():
            # read csv auto sniffs cols/types. CREATE OR REPLACE = safe re-runs
            con.execute(f"""
                        CREATE OR REPLACE TABLE {table} AS
                        SELECT ROW_NUMBER() OVER () AS event_id, * 
                        FROM read_csv_auto('{csv_path}', types = {{'Clock': 'VARCHAR'}})
                        """)
            # Count rows to confirm the load
            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"Loaded {table:18s} <- {csv_path.name:22s} ({n} rows)")
    finally:
        con.close()

if __name__ == "__main__":
    load_csv_staging()