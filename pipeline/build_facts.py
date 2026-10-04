import duckdb
from pathlib import Path
from pipeline.config import DB_PATH


def build_fact_events(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE OR REPLACE TABLE warehouse.fact_events AS
        SELECT
            ev.event_id,
            ev.period,
            ev.clock_seconds,
            ev.period_elapsed,
            ev.event,
            ev.zone,
            ev.x_coord,
            ev.y_coord,
            ev.x_coord_2,
            ev.y_coord_2,
            ev.detail_1,
            ev.detail_2,
            ev.detail_3,
            ev.detail_4,
            ev.is_home,
            ev.team_skaters,
            ev.opp_skaters,
            ev.strength_state,
            ev.skater_state,
            ev.is_shot,
            (ev.period - 1) * 1200 + ev.period_elapsed AS game_seconds,
            team.team_key  AS event_team_key, 
            opp.team_key  AS opponent_team_key, 
            player.player_key AS event_player_key,
            player2.player_key AS event_player2_key,
            game.game_key AS game_key
        FROM clean.events ev
        LEFT JOIN warehouse.dim_team team ON ev.event_team = team.team_name 
        LEFT JOIN warehouse.dim_team opp ON ev.opponent = opp.team_name 
        LEFT JOIN warehouse.dim_player player ON ev.event_player = player.player_name AND ev.event_team = player.team_name
        LEFT JOIN warehouse.dim_player player2 ON ev.player_2 = player2.player_name AND 
                CASE 
                    WHEN ev.event IN ('Faceoff Win', 'Penalty Taken', 'Zone Entry') THEN ev.opponent
                    ELSE ev.event_team
                END = player2.team_name
        LEFT JOIN warehouse.dim_game game ON ev.game_id = game.game_id 
        ORDER BY ev.event_id
    """)

def build_all(db_path: Path = DB_PATH) -> None:
    con = duckdb.connect(str(db_path))
    try:
        build_fact_events(con)
        for t in ("warehouse.fact_events",):
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Built {t:24s} ({n} rows)")
    finally:
        con.close()


if __name__ == "__main__":
    build_all()