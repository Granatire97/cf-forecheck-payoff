import duckdb
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
from dash.dash_table.Format import Format, Scheme
from pipeline.config import DB_PATH
import pandas as pd
from app.queries import get_puck_wins, get_shot_rate_grid, get_teams, get_strength_state, get_players, get_player_table, get_shot_rate_by_how_puck_win
from app.components.rink import build_rink

with duckdb.connect(str(DB_PATH), read_only=True) as con:
    # KPI values
    wins, rate, win_rate_count = con.execute(
        "SELECT COUNT(*), AVG(led_to_shot::INT), COUNT(*) * AVG(led_to_shot::INT) FROM warehouse.fact_puck_wins"
    ).fetchone()
    seconds_to_shot = con.execute(
        "SELECT MEDIAN(seconds_to_shot::INT) FROM warehouse.fact_puck_wins"
    ).fetchone()
    goals = con.execute(
        "SELECT COUNT(*) FROM warehouse.fact_puck_wins WHERE is_goal"
    ).fetchone()
    rebound = con.execute(
        "SELECT COUNT(*) FROM warehouse.fact_puck_wins WHERE is_goal AND win_type = 'Rebound'"
    ).fetchone()

    # Dfs for graphs/visuals/tables
    df = get_puck_wins(con)
    teams = get_teams(con)
    strength = get_strength_state(con)
    players = get_players(con)
    #player_table = get_player_table(con)
    #df2 = get_shot_rate_grid(con, teams)


app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # what the host runs when deployed

# Header HTML
analytics_header = html.Div(
    style={
        "backgroundColor": "#0B192C",  # Deep navy color from the image
        "padding": "30px 40px",
        "borderBottom": "3px solid #1a252f",
        "fontFamily": "sans-serif"
    },
    children=[
        dbc.Row([
            # Left side content (Title stack)
            dbc.Col([
                html.Span(
                    "OFFENSIVE-ZONE PUCK WINS", 
                    style={
                        "color": "#8A9Aad", 
                        "fontSize": "11px", 
                        "fontWeight": "bold", 
                        "letterSpacing": "1.5px",
                        "display": "block",
                        "marginBottom": "4px"
                    }
                ),
                html.H1(
                    "Forecheck Payoff", 
                    style={
                        "color": "#FFFFFF", 
                        "fontWeight": "800", 
                        "fontSize": "36px", 
                        "margin": "0 0 8px 0"
                    }
                ),
                html.P(
                    "Which ways of winning the puck back in the offensive zone turn into a shot within 10 seconds?", 
                    style={
                        "color": "#D1D5DB", 
                        "fontSize": "14px", 
                        "margin": "0"
                    }
                ),
            ], lg=8, md=7, sm=12, className="text-start"),
            
            # Right side content (Metadata stack)
            dbc.Col([
                html.Div(
                    "11 games · 2018 Olympics & 2019 Rivalry / Worlds", 
                    style={"fontSize": "12px", "color": "#A0AEC0", "marginBottom": "2px"}
                ),
                html.Div(
                    "Source: Stathletes Big Data Cup 2021", 
                    style={"fontSize": "11px", "color": "#718096"}
                ),
            ], lg=4, md=5, sm=12, className="text-end d-flex flex-column justify-content-end align-items-md-end pt-3 pt-md-0")
        ])
    ]
)


app.layout = dbc.Container([
    # Application Title Bar
    analytics_header,

    # Dropdowns for Filters
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Teams", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="team", options=teams, placeholder="All Teams", clearable=True)
                            ], width=4),
                        dbc.Col([
                            html.H5("Players", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="player", options=players, placeholder="All Players", clearable=True)

                        ], width=4),
                        dbc.Col([
                            html.H5("Strength", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="strength", options=[{"label": "Even Strength", "value":"EV"}, {"label": "Power Play", "value":"PP"},
                                                                 {"label": "Penalty Kill", "value":"PK"}, {"label": "Opponent Empty Net", "value":"EN"},
                                                                 {"label": "Extra Attacker", "value":"EA"}], placeholder="All Strength Options", clearable=True)

                        ], width=4),
                        ])
                    ])
                ], className="shadow-sm"), 
                width=12
            )
        ], className="mt-4"),
    # KPI rows
    dbc.Row([
        # KPIs
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("OZ puck wins"),
                dbc.CardBody([
                    html.H1(f"{wins:,}"),
                    html.P("Placeholder", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Led to a shot within 10s"),
                dbc.CardBody([
                    html.H1(f"{rate:.1%}"),
                    html.P(f"{win_rate_count:.0f} of {wins} wins", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Median time to shot"),
                dbc.CardBody([
                    html.H1(f"{seconds_to_shot[0]:.1f}s"),
                    html.P("Most shots come fast or not at all", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Goals off puck wins"),
                dbc.CardBody([
                    html.H1(goals),
                    html.P(f"{rebound[0]} of them off rebounds", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
    ], className="mt-4"),

    # Rink Graph & Shot Rate Graph
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Where puck wins pay off"),
                    dcc.Graph(id='hockey-rink',)
                ]),
            ]),
            width=6
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Shot rate by how the puck was won"),
                    dcc.Graph(id='shot-rate-won',)
                ]),
            ]),
            width=6
        ),
    ], className = "mt-4"),
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Players who turn wins into shots"),
                    dash_table.DataTable(
                        id='player-table',
                        columns = [{"name": "Player", "id": "Player"}, {"name": "Team", "id": "Team"}, 
                                   {"name": "OZ Wins", "id": "OZ Wins"}, {"name": "Led To Shot", "id": "Led To Shot"},
                                    {"name": "Rate", "id": "Rate", "type": "numeric", "format": Format(precision=1, scheme=Scheme.percentage)}],
                        style_table={'height': '400px', 'overflowY': 'auto', 'overflowX': 'auto'},
                        editable=False,
                        filter_action="native",
                        sort_action="native",
                        sort_mode="multi",
                        column_selectable="single",
                        row_selectable=False,
                        page_action="native", 
                        page_current= 0,
                        page_size= 25
                    )
                ])
            ])
        )
    ], className="mt-4")
])

@app.callback(Output("hockey-rink", "figure"), Output("shot-rate-won", "figure"), Output("player-table", "data"), Input("team", "value"), Input("player", "value"), Input("strength", "value"))
def update_graphs(team, player, strength):
    with duckdb.connect(str(DB_PATH), read_only=True) as con2:
        df2 = get_shot_rate_grid(con2, team, player, strength)
        event_shot_rate = get_shot_rate_by_how_puck_win(con2, team, player, strength)
        player_table_df = get_player_table(con2, team, player, strength)

    fig_rink = build_rink(df2)

    fig_bar = px.bar(
        event_shot_rate,
        x = "rate",
        y = "win_type",
        orientation="h",
        title="What happened right before the win",
        text="rate",
        color_discrete_sequence=["#1F4E8C"]
    )
    fig_bar.update_layout(yaxis={"categoryorder": "trace"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=80, t=50, b=0))
    x_max = event_shot_rate["rate"].max() if not event_shot_rate.empty else 1
    fig_bar.update_xaxes(visible=False, title="", range=[0, x_max * 1.25])
    fig_bar.update_yaxes(visible=True, title="")
    fig_bar.update_traces(texttemplate="%{text:.1%}",textposition="outside")

    return fig_rink, fig_bar, player_table_df.to_dict('records')

if __name__ == "__main__":
    app.run(debug=True)