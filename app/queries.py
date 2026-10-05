import duckdb
import pandas as pd

def get_puck_wins(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:

    result = con.execute("""
            SELECT 
                x_coord - 100 AS plot_x,
                y_coord - 42.5 AS plot_y,
                led_to_shot,
                win_type
            FROM warehouse.fact_puck_wins
    """)
    return result.df()

def get_shot_rate_grid(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:

    result = con.execute("""
            WITH grid AS (
            SELECT 
                LEAST(FLOOR((x_coord - 125) / 15), 4) AS bx,
                LEAST(FLOOR(y_coord / 17), 4) AS by_,
                COUNT(*) AS n,
                AVG(led_to_shot::INT) AS rate
            FROM warehouse.fact_puck_wins
            GROUP BY bx, by_
            )
            SELECT
                *,
                125 + bx * 15 + 7.5 - 100 AS cx,
                by_ * 17 + 8.5 - 42.5 AS cy
            FROM grid
    """)
    return result.df()