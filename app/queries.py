import duckdb
from pipeline.config import DB_PATH
from pathlib import Path

def get_puck_wins(con: duckdb.DuckDBPyConnection) -> list:

    sql = con.execute("""
            SELECT 
                x_coord - 100 AS plot_x,
                y_coord - 42.5 AS plot_y,
                led_to_shot,
                win_type
            FROM warehouse.fact_puck_wins
    """)

    return sql.df()

def main(db_path: Path = DB_PATH) -> list:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        get_puck_wins(con)
    finally:
        con.close()

    # one line summary to prove it works
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        print(con.sql("SELECT COUNT(*) AS wins, ROUND(AVG(led_to_shot::INT), 3) AS shot_rate FROM warehouse.fact_puck_wins"))

if __name__ == "__main__":
    main()