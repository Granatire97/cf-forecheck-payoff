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

def get_shot_rate_grid(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None) -> pd.DataFrame:

    result = con.execute("""
            WITH grid AS (
            SELECT 
                LEAST(FLOOR((x_coord - 125) / 15), 4) AS bx,
                LEAST(FLOOR(y_coord / 17), 4) AS by_,
                COUNT(*) AS n,
                AVG(led_to_shot::INT) AS rate
            FROM warehouse.fact_puck_wins
            JOIN warehouse.dim_team t
                ON t.team_key = warehouse.fact_puck_wins.event_team_key
            JOIN warehouse.dim_player p
                ON p.player_key = warehouse.fact_puck_wins.event_player_key
            WHERE ($team IS NULL OR t.team_name = $team)
                AND ($player IS NULL OR p.player_name = $player)
                AND ($strength IS NULL or warehouse.fact_puck_wins.strength_state = $strength)
            GROUP BY bx, by_
            )
            SELECT
                *,
                125 + bx * 15 + 7.5 - 100 AS cx,
                by_ * 17 + 8.5 - 42.5 AS cy
            FROM grid
    """, {"team":team, "player":player, "strength":strength})
    return result.df()

def get_teams(con: duckdb.DuckDBPyConnection) -> list[str]:

    result = con.execute("""
            SELECT
                team_name
            FROM warehouse.dim_team
            ORDER BY team_name

    """)
    return [r[0] for r in result.fetchall()]

def get_players(con: duckdb.DuckDBPyConnection) -> list[str]:

    result = con.execute("""
            SELECT DISTINCT
                p.player_name
            FROM warehouse.fact_puck_wins pw
            JOIN warehouse.dim_player p 
                ON p.player_key = pw.event_player_key
            ORDER BY p.player_name

    """)
    return [r[0] for r in result.fetchall()]

def get_strength_state(con: duckdb.DuckDBPyConnection) -> list[str]:

    result = con.execute("""
            SELECT DISTINCT
                strength_state
            FROM warehouse.fact_puck_wins
            ORDER BY strength_state
    """)
    return [r[0] for r in result.fetchall()]

def get_player_table(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:

    result = con.execute("""
            SELECT 
                p.player_name as Player, 
                p.team_name as Team,
                COUNT(*) AS "OZ Wins", 
                SUM(led_to_shot) AS "Led To Shot", 
                AVG(led_to_shot::INT) AS Rate
            FROM warehouse.fact_puck_wins fw
            JOIN warehouse.dim_player p ON p.player_key = fw.event_player_key
            GROUP BY p.player_name, p.team_name
            HAVING COUNT(*) > 20
            ORDER BY COUNT(*) DESC
    """)
    return result.df()