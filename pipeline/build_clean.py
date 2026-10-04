import duckdb
from pathlib import Path
from pipeline.config import DB_PATH



def transform_events(con: duckdb.DuckDBPyConnection) -> None:
    """Events: rename, derive game, clock, strength, zone, then drop duplicates"""
    con.execute("""
        CREATE OR REPLACE TABLE clean.events AS
        SELECT
            event_id,
            DENSE_RANK() OVER (ORDER BY game_date, "Home Team", "Away Team") AS game_id,
            game_date,
            CASE
                WHEN "Home Team" LIKE 'Olympic%' THEN 'Olympic'
                ELSE 'NCAA'
            END AS league,
            REPLACE("Home Team", 'Olympic (Women) - ', '') AS home_team,
            REPLACE("Away Team", 'Olympic (Women) - ', '') AS away_team,
            REPLACE(Team, 'Olympic (Women) - ', '') AS event_team,
            Period                       AS period,
            TRIM(Clock)                  AS clock,
            CAST(SPLIT_PART(Clock, ':', 1) AS INTEGER) * 60 + CAST(SPLIT_PART(Clock, ':', 2) AS INTEGER) AS clock_seconds,
            1200 - clock_seconds         AS period_elapsed,
            "Home Team Skaters"          AS home_team_skaters,
            "Away Team Skaters"          AS away_team_skaters,
            "Home Team Goals"            AS home_team_goals,
            "Away Team Goals"            AS away_team_goals,
            TRIM(Player)                 AS event_player,
            TRIM(event)                  AS event,
            "X Coordinate"               AS x_coord,
            "Y Coordinate"               AS y_coord,
            TRIM("Detail 1")             AS detail_1,
            TRIM("Detail 2")             AS detail_2,
            "Detail 3"                   AS detail_3,
            "Detail 4"                   AS detail_4, 
            TRIM("Player 2")             AS player_2,
            "X Coordinate 2"             AS x_coord_2,
            "Y Coordinate 2"             AS y_coord_2,
            event_team = home_team       AS is_home,
            CASE 
                WHEN is_home THEN away_team
                ELSE home_team
            END AS opponent,
            CASE 
                WHEN is_home THEN home_team_skaters
                ELSE away_team_skaters
            END AS team_skaters,
            CASE 
                WHEN is_home THEN away_team_skaters
                ELSE home_team_skaters
            END AS opp_skaters,
            CASE
                WHEN team_skaters = 6 THEN 'EA'
                WHEN opp_skaters = 6 THEN 'EN'
                WHEN team_skaters > opp_skaters THEN 'PP'
                WHEN team_skaters < opp_skaters THEN 'PK'
            ELSE 'EV'
            END AS strength_state,
            team_skaters || 'v' || opp_skaters AS skater_state,
            CASE 
                WHEN x_coord >= 125 THEN 'OZ'
                WHEN x_coord <= 75 THEN 'DZ'
                ELSE 'NZ'
            END AS zone,
            CASE
                WHEN event IN ('Shot', 'Goal') THEN 1
                ELSE 0
            END AS is_shot
        FROM staging.events
        ORDER BY event_id
    """)

    con.execute("""
        DELETE FROM clean.events
        WHERE event_id NOT IN (
            SELECT keep_id FROM (
                    SELECT min(event_id) AS keep_id, * EXCLUDE (event_id)
                    FROM clean.events
                    GROUP BY ALL
                )
            )
    """)

def transform_all(db_path: Path = DB_PATH) -> None:
    """Run all transforms."""
    con = duckdb.connect(str(db_path))
    try:
        transform_events(con)
        # Confirm
        for t in ("clean.events",):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Built {t:16s} ({n} rows)")
    finally:
        con.close()


if __name__ == "__main__":
    transform_all()