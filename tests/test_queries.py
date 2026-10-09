"""Query checks. Filters and breakdowns must describe the same puck wins."""

import pytest

from app.queries import (
    get_end_reason_on_win,
    get_player_table,
    get_shot_rate_by_how_puck_win,
    get_shot_rate_grid,
    get_summary,
    get_win_type,
)

ALLOWED_WIN_TYPES = {
    "Rebound",
    "Faceoff",
    "Forecheck Retrieval",
    "Forced Turnover",
    "Support",
    "Other / Loose Puck",
}
ALLOWED_END_REASONS = {
    "shot",
    "opponent_possession",
    "time_expired",
    "stoppage",
}

FILTERS = [
    {},
    {"team": "Canada"},
    {"team": "United States"},
    {"team": "Finland"},
    {"player": "Hilary Knight"},
    {"player": "Rebecca Johnston"},
    {"strength": "EV"},
    {"strength": "PP"},
    {"strength": "PK"},
    {"team": "Canada", "strength": "EV"},
    {"team": "Canada", "player": "Marie-Philip Poulin"},
    {"team": "Canada", "player": "Hilary Knight"},
    {"win_type": "Rebound"},
    {"win_type": "Forecheck Retrieval"},
    {"team": "Canada", "win_type": "Forced Turnover"},
    {"strength": "PP", "win_type": "Faceoff"},
]


def _filter_id(filters):
    if not filters:
        return "unfiltered"
    return ",".join(f"{key}={value}" for key, value in filters.items())


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("wins", 2219),
        ("recoveries", 1955),
        ("takeaways", 264),
        ("shots", 905),
        ("goals", 23),
        ("rebound_goals", 11),
    ],
)
def test_unfiltered_summary(con, metric, expected):
    """The unfiltered summary is the headline count for the whole tournament slice."""
    assert get_summary(con)[metric] == expected


def test_canada_summary_wins(con):
    """A team filter must count only that team's offensive-zone puck wins."""
    assert get_summary(con, team="Canada")["wins"] == 1173


def test_mismatched_team_and_player_returns_zero_wins(con):
    """A player who does not play for the selected team yields an empty result, not an error."""
    summary = get_summary(con, team="Canada", player="Hilary Knight")
    assert summary["wins"] == 0


@pytest.mark.parametrize("filters", FILTERS, ids=_filter_id)
def test_shot_rate_grid_counts_match_summary(con, filters):
    """Rink cells partition the same wins the summary counts for those filters."""
    grid = get_shot_rate_grid(con, **filters)
    summary = get_summary(con, **filters)
    assert grid["n"].sum() == summary["wins"]


@pytest.mark.parametrize("filters", FILTERS, ids=_filter_id)
def test_win_type_counts_match_summary(con, filters):
    """The win-type breakdown partitions the same wins the summary counts."""
    if "win_type" in filters:
        pytest.skip("The bar chart always shows every win type, so it does not take this filter.")
    by_type = get_shot_rate_by_how_puck_win(con, **filters)
    summary = get_summary(con, **filters)
    assert by_type["wins"].sum() == summary["wins"]


@pytest.mark.parametrize("filters", FILTERS, ids=_filter_id)
def test_end_reason_totals_match_summary_wins(con, filters):
    """End reasons partition the same wins the summary counts for those filters."""
    reasons = get_end_reason_on_win(con, **filters)
    summary = get_summary(con, **filters)
    assert reasons["totals"].sum() == summary["wins"]


@pytest.mark.parametrize("filters", FILTERS, ids=_filter_id)
def test_shot_end_reason_matches_summary_shots(con, filters):
    """Wins that end in a shot are the shots the summary counts."""
    reasons = get_end_reason_on_win(con, **filters)
    shot_rows = reasons.loc[reasons["end_reason"] == "shot", "totals"]
    shot_total = shot_rows.iloc[0] if len(shot_rows) else 0
    assert shot_total == get_summary(con, **filters)["shots"]


def test_end_reasons_are_classified(con):
    """The end-reason chart only has the four ways a puck-win sequence can stop."""
    reasons = set(get_end_reason_on_win(con)["end_reason"])
    assert reasons <= ALLOWED_END_REASONS


def test_get_win_type_lists_allowed_values_once(con):
    """The win-type dropdown offers each classified type once, and nothing else."""
    win_types = get_win_type(con)
    assert set(win_types) <= ALLOWED_WIN_TYPES and len(win_types) == len(set(win_types))


def test_win_type_filter_matches_bar_chart(con):
    """Filtering the summary to one win type matches that type's bar on the comparison chart."""
    chart = get_shot_rate_by_how_puck_win(con)
    chart_wins = dict(zip(chart["win_type"], chart["wins"]))
    summary_wins = {
        win_type: get_summary(con, win_type=win_type)["wins"]
        for win_type in get_win_type(con)
    }
    assert summary_wins == {win_type: chart_wins.get(win_type) for win_type in summary_wins}


def test_player_table_win_type_filter_uses_five_win_minimum(con):
    """A win-type filter lowers the player-table cutoff to 5 wins and still lists players."""
    table = get_player_table(con, win_type="Forecheck Retrieval")
    assert len(table) >= 1 and table["OZ Wins"].min() >= 5


def test_unfiltered_player_table_keeps_players_with_at_least_20_wins(con):
    """The default player table drops low-volume players so the rate is not noise."""
    table = get_player_table(con)
    assert table["OZ Wins"].min() >= 20


def test_player_filter_returns_a_player_below_20_wins(con):
    """Choosing a player shows that player's row even with fewer than 20 wins."""
    name, wins = con.execute("""
        SELECT p.player_name, COUNT(*)
        FROM warehouse.fact_puck_wins AS puck_wins
        JOIN warehouse.dim_player AS p ON p.player_key = puck_wins.event_player_key
        GROUP BY p.player_name
        HAVING COUNT(*) < 20
        ORDER BY COUNT(*), p.player_name
        LIMIT 1
    """).fetchone()
    table = get_player_table(con, player=name)
    assert list(table["Player"]) == [name]
    assert table.loc[0, "OZ Wins"] == wins
    assert wins < 20
