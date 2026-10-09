import duckdb
import pandas as pd

def get_shot_rate_grid(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None, win_type: str | None = None) -> pd.DataFrame:

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
                AND ($win_type IS NULL or warehouse.fact_puck_wins.win_type = $win_type)
            GROUP BY bx, by_
            )
            SELECT
                *,
                125 + bx * 15 + 7.5 - 100 AS cx,
                by_ * 17 + 8.5 - 42.5 AS cy
            FROM grid
    """, {"team":team, "player":player, "strength":strength, "win_type":win_type})
    return result.df()

def get_teams(con: duckdb.DuckDBPyConnection) -> list[str]:

    result = con.execute("""
            SELECT
                team_name
            FROM warehouse.dim_team
            ORDER BY team_name

    """)
    return [r[0] for r in result.fetchall()]

def get_players(con: duckdb.DuckDBPyConnection, team: str | None = None) -> list[str]:

    result = con.execute("""
            SELECT DISTINCT
                p.player_name
            FROM warehouse.fact_puck_wins pw
            JOIN warehouse.dim_player p 
                ON p.player_key = pw.event_player_key
            WHERE $team IS NULL OR p.team_name = $team
            ORDER BY p.player_name

    """, {"team":team})
    return [r[0] for r in result.fetchall()]

def get_win_type(con: duckdb.DuckDBPyConnection) -> list[str]:

    result = con.execute("""
            SELECT DISTINCT
                fw.win_type
            FROM warehouse.fact_puck_wins fw
            ORDER BY fw.win_type

    """)
    return [r[0] for r in result.fetchall()]

def get_player_table(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None, win_type: str | None = None) -> pd.DataFrame:

    result = con.execute("""
            SELECT 
                p.player_name as Player, 
                p.team_name as Team,
                COUNT(*) AS "OZ Wins", 
                SUM(led_to_shot) AS "Led To Shot", 
                AVG(led_to_shot::INT) AS Rate
            FROM warehouse.fact_puck_wins fw
            JOIN warehouse.dim_team t
                ON t.team_key = fw.event_team_key
            JOIN warehouse.dim_player p
                ON p.player_key = fw.event_player_key
            WHERE ($team IS NULL OR t.team_name = $team)
                AND ($player IS NULL OR p.player_name = $player)
                AND ($strength IS NULL or fw.strength_state = $strength)
                AND ($win_type IS NULL or fw.win_type = $win_type)
            GROUP BY p.player_name, p.team_name
            HAVING COUNT(*) >= CASE WHEN $player IS NOT NULL THEN 1
                        WHEN $strength IS NOT NULL OR $win_type IS NOT NULL THEN 5
                        ELSE 20 END
            ORDER BY COUNT(*) DESC
    """, {"team":team, "player":player, "strength":strength, "win_type":win_type})
    return result.df()

def get_shot_rate_by_how_puck_win(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None) -> pd.DataFrame:

    result = con.execute("""
            SELECT
                w.win_type,
                MEDIAN(w.seconds_to_shot::INT) AS med_seconds_to_shot,
                COUNT(*) FILTER (WHERE w.is_goal) AS total_goals,
                COUNT(*) AS wins,
                AVG(led_to_shot::INT) AS rate
            FROM warehouse.fact_puck_wins w
            JOIN warehouse.dim_team t
                ON t.team_key = w.event_team_key
            JOIN warehouse.dim_player p
                ON p.player_key = w.event_player_key
            WHERE ($team IS NULL OR t.team_name = $team)
                AND ($player IS NULL OR p.player_name = $player)
                AND ($strength IS NULL or w.strength_state = $strength)
            GROUP BY w.win_type
            ORDER BY rate
    """, {"team":team, "player":player, "strength":strength})
    return result.df()

def get_summary(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None, win_type: str | None = None) -> pd.Series:

    result = con.execute("""
            SELECT
                COUNT(*)                                                       AS wins,
                COUNT(*) FILTER (WHERE fw.event = 'Puck Recovery')              AS recoveries,
                COUNT(*) FILTER (WHERE fw.event = 'Takeaway')                   AS takeaways,
                COUNT(*) FILTER (WHERE fw.is_goal)                              AS goals,
                COUNT(*) FILTER (WHERE fw.is_goal AND fw.win_type = 'Rebound')  AS rebound_goals,
                COALESCE(SUM(led_to_shot::INT), 0)                              AS shots,
                AVG(led_to_shot::INT)                                           AS rate,
                MEDIAN(seconds_to_shot)                                         AS med_secs
            FROM warehouse.fact_puck_wins fw
            JOIN warehouse.dim_team t
                ON t.team_key = fw.event_team_key
            JOIN warehouse.dim_player p
                ON p.player_key = fw.event_player_key
            WHERE ($team IS NULL OR t.team_name = $team)
                AND ($player IS NULL OR p.player_name = $player)
                AND ($strength IS NULL or fw.strength_state = $strength)
                AND ($win_type IS NULL or fw.win_type = $win_type)
    """, {"team":team, "player":player, "strength":strength, "win_type":win_type})
    return result.df().iloc[0]

def get_end_reason_on_win(con: duckdb.DuckDBPyConnection, team: str | None = None, player: str | None = None, strength: str | None = None, win_type: str | None = None) -> pd.DataFrame:

    result = con.execute("""
            SELECT
                w.end_reason,
                COUNT(*) AS totals
            FROM warehouse.fact_puck_wins w
            JOIN warehouse.dim_team t
                ON t.team_key = w.event_team_key
            JOIN warehouse.dim_player p
                ON p.player_key = w.event_player_key
            WHERE ($team IS NULL OR t.team_name = $team)
                AND ($player IS NULL OR p.player_name = $player)
                AND ($strength IS NULL or w.strength_state = $strength)
                AND ($win_type IS NULL or w.win_type = $win_type)
            GROUP BY w.end_reason
            ORDER BY totals DESC
    """, {"team":team, "player":player, "strength":strength, "win_type":win_type})
    return result.df()