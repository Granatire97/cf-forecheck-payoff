import duckdb
from pathlib import Path
from pipeline.config import DB_PATH

def build_dim_game(con: duckdb.DuckDBPyConnection) -> None:
    """Game dimension: surrogate key + natural key + attributes."""
    con.execute("""
        CREATE OR REPLACE TABLE warehouse.dim_game AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY game_id) AS game_key,  -- surrogate
            game_id,                                           -- natural
            game_date,
            league,
            home_team,            
            away_team,
            COUNT(*) FILTER (WHERE event = 'Goal' AND is_home) AS home_score,
            COUNT(*) FILTER (WHERE event = 'Goal' AND NOT is_home) AS away_score,
            home_score + away_score           AS total_game_goals,
            CASE
                WHEN home_score > away_score THEN home_team
                WHEN away_score > home_score THEN away_team
                ELSE 'Shootout'
            END                               AS winner
        FROM clean.events
        GROUP BY game_id, game_date, league, home_team, away_team
    """)

def build_dim_team(con: duckdb.DuckDBPyConnection) -> None:
    """Team dimension: surrogate key + natural key + descriptive attributes."""
    con.execute("""
        CREATE OR REPLACE TABLE warehouse.dim_team AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY team_name) AS team_key,   -- surrogate key
            team_name,
            league
        FROM (
            SELECT DISTINCT event_team AS team_name, league
            FROM clean.events
        )
    """)


def build_dim_player(con: duckdb.DuckDBPyConnection) -> None:
    """Player dimension: surrogate key + natural key + attributes."""
    con.execute("""
        CREATE OR REPLACE TABLE warehouse.dim_player AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY team_name, player_name) AS player_key,  -- surrogate
            player_name,
            team_name,
            league
        FROM (
            SELECT 
                event_player AS player_name,
                event_team AS team_name, 
                league
            FROM clean.events
                
            UNION
            
            SELECT 
                player_2,
                CASE 
                    WHEN event IN ('Faceoff Win', 'Penalty Taken', 'Zone Entry') THEN opponent
                    ELSE event_team
                END,
                league
            FROM clean.events
            WHERE player_2 IS NOT NULL 
        )
    """)

def build_all(db_path: Path = DB_PATH) -> None:
    """Build all dimension tables."""
    con = duckdb.connect(str(db_path))
    try:
        build_dim_game(con)
        build_dim_team(con)
        build_dim_player(con)
        for t in ("warehouse.dim_team", "warehouse.dim_player", "warehouse.dim_game"):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Built {t:24s} ({n} rows)")
    finally:
        con.close()


if __name__ == "__main__":
    build_all()