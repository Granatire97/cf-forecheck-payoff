"""Run the full hockey pipeline end to end, in order."""
import duckdb
from pipeline.config import DB_PATH
from pipeline.setup_warehouse import create_warehouse
from pipeline.build_staging import load_csv_staging
from pipeline.build_clean import transform_all
from pipeline.build_dims import build_all as build_dimensions
from pipeline.build_facts import build_all as build_facts
from pipeline.build_puck_wins import build_all as build_puck_wins


def pipeline():
    steps = [
        ("create_warehouse", create_warehouse),
        ("load_csv_staging", load_csv_staging),
        ("build_clean", transform_all),
        ("build_dims", build_dimensions),
        ("build_fact_events", build_facts),
        ("build_puck_wins", build_puck_wins)
    ]
    for name, func in steps:
        print(f"Running {name}...")
        func(db_path=DB_PATH)  

def main():
    pipeline()

    # one line summary to prove it works
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        print(con.sql("SELECT COUNT(*) AS wins, ROUND(AVG(led_to_shot::INT), 3) AS shot_rate FROM warehouse.fact_puck_wins"))

if __name__ == "__main__":
    main()