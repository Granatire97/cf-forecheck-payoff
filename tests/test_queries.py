"""Query checks. Filters and breakdowns must describe the same puck wins."""

import pytest

from app.queries import (
    get_player_table,
    get_shot_rate_by_how_puck_win,
    get_shot_rate_grid,
    get_summary,
)

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
    by_type = get_shot_rate_by_how_puck_win(con, **filters)
    summary = get_summary(con, **filters)
    assert by_type["wins"].sum() == summary["wins"]


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
