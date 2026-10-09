"""Warehouse checks. These lock the grain and the rules the Dash app assumes."""


def test_clean_events_row_count(con):
    """The Olympic filter should leave the known event volume for every later table."""
    n = con.execute("SELECT COUNT(*) FROM clean.events").fetchone()[0]
    assert n == 20520


def test_clean_events_has_no_full_duplicates(con):
    """Identical events, ignoring the row id, would double-count shots and puck wins."""
    duplicate_groups = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT * EXCLUDE (event_id)
            FROM clean.events
            GROUP BY ALL
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert duplicate_groups == 0


def test_period_elapsed_stays_inside_a_period(con):
    """Elapsed time comes from the clock and must stay inside a 20-minute period."""
    outside = con.execute("""
        SELECT COUNT(*)
        FROM clean.events
        WHERE period_elapsed IS NULL
           OR period_elapsed < 0
           OR period_elapsed > 1200
    """).fetchone()[0]
    assert outside == 0


def test_fact_events_matches_clean_row_count(con):
    """Dimension joins must not fan out, or one event would become many facts."""
    fact_rows, clean_rows = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM warehouse.fact_events),
            (SELECT COUNT(*) FROM clean.events)
    """).fetchone()
    assert fact_rows == clean_rows


def test_fact_events_required_keys_are_populated(con):
    """Every event must resolve to a game, both teams, and the acting player."""
    nulls = con.execute("""
        SELECT
            COUNT(*) FILTER (WHERE game_key IS NULL),
            COUNT(*) FILTER (WHERE event_team_key IS NULL),
            COUNT(*) FILTER (WHERE opponent_team_key IS NULL),
            COUNT(*) FILTER (WHERE event_player_key IS NULL)
        FROM warehouse.fact_events
    """).fetchone()
    assert nulls == (0, 0, 0, 0)


def test_event_player2_key_null_matches_missing_player_2(con):
    """The second-player key is null exactly when the event has no player 2."""
    mismatched = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_events AS fact
        JOIN clean.events AS clean ON fact.event_id = clean.event_id
        WHERE (fact.event_player2_key IS NULL) <> (clean.player_2 IS NULL)
    """).fetchone()[0]
    assert mismatched == 0


def test_event_team_differs_from_opponent(con):
    """A team cannot be listed as its own opponent on an event."""
    same_team = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_events
        WHERE event_team_key = opponent_team_key
    """).fetchone()[0]
    assert same_team == 0


def test_dim_game_row_count(con):
    """The tournament slice is 11 games; a bad game key would split or merge them."""
    n = con.execute("SELECT COUNT(*) FROM warehouse.dim_game").fetchone()[0]
    assert n == 11


def test_dim_team_row_count(con):
    """Four clubs play in this slice; team filters depend on that list."""
    n = con.execute("SELECT COUNT(*) FROM warehouse.dim_team").fetchone()[0]
    assert n == 4


def test_dim_player_name_and_team_are_unique(con):
    """One row per player and team keeps event joins from multiplying."""
    duplicate_pairs = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT player_name, team_name
            FROM warehouse.dim_player
            GROUP BY player_name, team_name
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert duplicate_pairs == 0


def test_fact_puck_wins_row_count(con):
    """Offensive-zone recoveries and takeaways are the population the app analyzes."""
    n = con.execute("SELECT COUNT(*) FROM warehouse.fact_puck_wins").fetchone()[0]
    assert n == 2219


def test_fact_puck_wins_event_id_is_unique(con):
    """Each puck win is one event; a repeated id would double its shot outcome."""
    rows, distinct_ids = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT event_id)
        FROM warehouse.fact_puck_wins
    """).fetchone()
    assert rows == distinct_ids


def test_fact_puck_wins_are_in_the_offensive_zone(con):
    """The fact is defined as an offensive-zone win, which starts at x = 125."""
    outside = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_puck_wins
        WHERE x_coord IS NULL OR x_coord < 125
    """).fetchone()[0]
    assert outside == 0


def test_fact_puck_wins_events_are_recoveries_or_takeaways(con):
    """Only puck recoveries and takeaways count as winning the puck."""
    events = {
        row[0]
        for row in con.execute(
            "SELECT DISTINCT event FROM warehouse.fact_puck_wins"
        ).fetchall()
    }
    assert events <= {"Puck Recovery", "Takeaway"}


def test_fact_puck_wins_win_type_is_classified(con):
    """How the puck was won must stay inside the categories the app charts."""
    win_types = {
        row[0]
        for row in con.execute(
            "SELECT DISTINCT win_type FROM warehouse.fact_puck_wins"
        ).fetchall()
    }
    assert win_types <= {
        "Rebound",
        "Faceoff",
        "Forecheck Retrieval",
        "Forced Turnover",
        "Support",
        "Other / Loose Puck",
    }


def test_led_to_shot_has_a_shot_event(con):
    """A win marked as leading to a shot must point at that shot."""
    missing = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_puck_wins
        WHERE led_to_shot AND shot_event_id IS NULL
    """).fetchone()[0]
    assert missing == 0


def test_seconds_to_shot_stays_within_ten_seconds(con):
    """Shots credited to a puck win have to fall inside the 10-second window."""
    outside = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_puck_wins
        WHERE led_to_shot
          AND (
              seconds_to_shot IS NULL
              OR seconds_to_shot < 0
              OR seconds_to_shot > 10
          )
    """).fetchone()[0]
    assert outside == 0


def test_no_shot_event_when_win_did_not_lead_to_shot(con):
    """Wins that did not produce a shot must not keep a shot event id."""
    with_shot = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_puck_wins
        WHERE NOT led_to_shot
          AND shot_event_id IS NOT NULL
    """).fetchone()[0]
    assert with_shot == 0


def test_fact_puck_wins_end_reason_is_classified(con):
    """How a possession ended must stay inside the categories the app charts."""
    reasons = {
        row[0]
        for row in con.execute(
            "SELECT DISTINCT end_reason FROM warehouse.fact_puck_wins"
        ).fetchall()
    }
    assert reasons <= {"shot", "opponent_possession", "time_expired", "stoppage"}


def test_shot_end_reason_matches_led_to_shot(con):
    """A shot end reason is recorded exactly when the win led to a shot."""
    mismatched = con.execute("""
        SELECT COUNT(*)
        FROM warehouse.fact_puck_wins
        WHERE (end_reason = 'shot') IS DISTINCT FROM led_to_shot
    """).fetchone()[0]
    assert mismatched == 0


def test_overall_shot_rate(con):
    """The share of puck wins that become a shot is the rate the app leads with."""
    rate = con.execute(
        "SELECT ROUND(AVG(led_to_shot::INT), 3) FROM warehouse.fact_puck_wins"
    ).fetchone()[0]
    assert rate == 0.408
