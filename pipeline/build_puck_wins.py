import duckdb
from pathlib import Path
from pipeline.config import DB_PATH


def build_fact_puck_wins(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE OR REPLACE TABLE warehouse.fact_puck_wins AS
        WITH events_lagged AS (
            SELECT 
                *,
                LAG(event) OVER (PARTITION BY game_key ORDER BY event_id) AS previous_event,
                LAG(event_team_key) OVER (PARTITION BY game_key ORDER BY event_id) AS previous_event_team_key,
                LAG(detail_1) OVER (PARTITION BY game_key ORDER BY event_id) AS previous_detail_1,
                LAG(period) OVER (PARTITION BY game_key ORDER BY event_id) AS previous_period
            FROM warehouse.fact_events
        ), 
        wins AS (
            SELECT 
                CASE 
                    WHEN previous_period <> period THEN  'Other / Loose Puck'
                    WHEN previous_event = 'Shot' AND previous_event_team_key = event_team_key THEN 'Rebound'
                    WHEN previous_event = 'Faceoff Win' AND previous_event_team_key = event_team_key THEN 'Faceoff'
                    WHEN (previous_event = 'Dump In/Out' OR (previous_detail_1 = 'Dumped' AND previous_event = 'Zone Entry')) AND previous_event_team_key = event_team_key THEN 'Forecheck Retrieval'
                    WHEN event = 'Takeaway' OR previous_event_team_key = opponent_team_key THEN 'Forced Turnover'
                    ELSE 'Support'
                END AS win_type,
                previous_event_team_key,
                previous_event,
                previous_detail_1,
                event_team_key,
                game_key, 
                period,
                x_coord,
                y_coord,
                game_seconds,
                event_id,
                event, 
                opponent_team_key,
                event_player_key,
                strength_state, 
                skater_state
            FROM events_lagged
            WHERE event IN ('Puck Recovery', 'Takeaway')
                AND zone = 'OZ'
        ),
        window_events AS (
            SELECT 
                w.game_key AS win_game_key,
                w.event_id AS win_event_id,
                w.period AS win_period, 
                w.win_type AS win_type,
                w.event_team_key AS win_event_team_key,
                w.game_seconds AS win_game_seconds,
                e.event_id AS following_event_id,
                e.game_seconds AS following_game_seconds,
                e.event_team_key AS following_team_key,
                e.event AS following_event,
                e.detail_1 AS following_detail_1,
                e.is_shot AS following_is_shot,
                (e.game_seconds - w.game_seconds) AS seconds_since_win
            FROM wins w
            JOIN warehouse.fact_events e
                ON w.game_key = e.game_key
                AND w.period = e.period
                AND e.event_id > w.event_id
                AND e.game_seconds <= (w.game_seconds + 10)
        ),
        first_end AS (
            SELECT
                win_event_id, 
                MIN(following_event_id) FILTER (WHERE (following_team_key <> win_event_team_key) OR following_event IN ('Faceoff Win', 'Penalty Taken')) AS end_event_id
            FROM window_events
            GROUP BY win_event_id
        ),
        first_shot AS (
            SELECT
                win_event_id, 
                MIN(following_event_id) FILTER (WHERE (following_is_shot = 1) AND (following_team_key = win_event_team_key)) AS shot_event_id
            FROM window_events
            GROUP BY win_event_id
        ), 
        outcome AS (
            SELECT
                w.event_id AS win_event_id,
                first_end.end_event_id AS end_event_id,
                first_shot.shot_event_id IS NOT NULL AND (first_end.end_event_id IS NULL OR first_shot.shot_event_id < first_end.end_event_id) AS led_to_shot,
                CASE 
                    WHEN led_to_shot THEN first_shot.shot_event_id
                END AS shot_event_id
            FROM wins w
            LEFT JOIN first_end ON first_end.win_event_id = w.event_id
            LEFT JOIN first_shot ON first_shot.win_event_id = w.event_id
        )
        SELECT
            w.*,
            o.led_to_shot,
            o.shot_event_id,
            e.game_seconds - w.game_seconds AS seconds_to_shot,
            e.x_coord                       AS shot_x,
            e.y_coord                       AS shot_y,
            e.detail_1                      AS shot_type,
            e.detail_2                      AS shot_result,
            e.event = 'Goal'                AS is_goal,
            CASE
                WHEN o.led_to_shot THEN 'shot'
                WHEN ev.event IN ('Faceoff Win', 'Penalty Taken') THEN 'stoppage'
                WHEN ev.event_id IS NOT NULL THEN 'opponent_possession'
                ELSE 'time_expired'
            END                             AS end_reason
            FROM wins w
            LEFT JOIN outcome o 
                ON o.win_event_id = w.event_id
            LEFT JOIN warehouse.fact_events e
                ON e.event_id = o.shot_event_id
            LEFT JOIN warehouse.fact_events ev ON ev.event_id = o.end_event_id
            ORDER BY w.event_id
            
    """)

def build_all(db_path: Path = DB_PATH) -> None:
    con = duckdb.connect(str(db_path))
    try:
        build_fact_puck_wins(con)
        for t in ("warehouse.fact_puck_wins",):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Built {t:24s} ({n} rows)")
    finally:
        con.close()


if __name__ == "__main__":
    build_all()