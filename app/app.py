import duckdb
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
from dash.dash_table.Format import Format, Scheme
from pipeline.config import DB_PATH
import pandas as pd
from app.queries import get_shot_rate_grid, get_teams, get_players, get_player_table, get_shot_rate_by_how_puck_win, get_summary, get_win_type, get_end_reason_on_win
from app.components.rink import build_rink

with duckdb.connect(str(DB_PATH), read_only=True) as con:
    # Dropdown options
    teams = get_teams(con)
    players = get_players(con)
    win_type = get_win_type(con)


app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# Header HTML
analytics_header = html.Div(
    style={
        "backgroundColor": "#0B192C",
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
                            ], width=3),
                        dbc.Col([
                            html.H5("Players", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="player", options=players, placeholder="All Players", clearable=True)

                        ], width=3),
                        dbc.Col([
                            html.H5("Strength", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="strength", options=[{"label": "Even Strength", "value":"EV"}, {"label": "Power Play", "value":"PP"},
                                                                 {"label": "Penalty Kill", "value":"PK"}, {"label": "Opponent Empty Net", "value":"EN"},
                                                                 {"label": "Extra Attacker", "value":"EA"}], placeholder="All Strength Options", clearable=True)

                        ], width=3),
                        dbc.Col([
                            html.H5("Win Type", className="card-title text-muted fw-bold"),
                            dcc.Dropdown(id="win-type", options=win_type, placeholder="All Win Type Options", clearable=True)

                        ], width=3),
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
                    html.H1(id="kpi-wins"),
                    html.P(id="kpi-wins-sub", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Led to a shot within 10s"),
                dbc.CardBody([
                    html.H1(id="kpi-rate"),
                    html.P(id="kpi-rate-sub", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Median time to shot"),
                dbc.CardBody([
                    html.H1(id="kpi-med-secs"),
                    html.P("Most shots come fast or not at all", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ]),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Goals off puck wins"),
                dbc.CardBody([
                    html.H1(id="kpi-goals"),
                    html.P(id="kpi-goals-sub", style = {'fontSize': '12px'}, className="card-text"),
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
                    html.Div(
                        [
                            html.H4("Where puck wins pay off", className="card-title text-muted mb-0 fw-bold"),
                            html.Span("Shot rate by location - wins per cell (hover)", className="text-muted", style = {'fontSize': '12px'}),
                        ],
                            className="d-flex justify-content-between align-items-center",
                    ),
                    dcc.Graph(id='hockey-rink',)
                ]),
            ], className="h-100"),
            width=6
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Shot rate by how the puck was won", className="card-title text-muted fw-bold"),
                    html.H6("What happened right before the win", className="text-muted"),
                    dcc.Graph(id='shot-rate-won',)
                ]),
            ], className="h-100"),
            width=6
        ),
    ], className = "mt-4"),
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.Div(
                        [
                            html.H4("Players who turn wins into shots", className="card-title text-muted mb-0 fw-bold"),
                            html.Span("Min. 20 OZ Wins", className="text-muted", style = {'fontSize': '12px'}),
                        ],
                            className="d-flex justify-content-between align-items-center",
                    ),
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
                        row_selectable=False,
                        page_action="native", 
                        page_current= 0,
                        page_size= 25
                    )
                ])
            ], className="h-100"),
            width=6
        ), 
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("How the 10 seconds end", className="card-title text-muted fw-bold"),
                    html.H6("First thing that happened after the win", className="text-muted"),
                    dcc.Graph(id='end-reason',)
                ]),
            ], className="h-100"),
            width=6
        ),
    ], className="mt-4")
])

@app.callback(Output("hockey-rink", "figure"), Output("shot-rate-won", "figure"), Output("player-table", "data"), Output("end-reason", "figure"),
              Output("kpi-wins", "children"), Output("kpi-wins-sub", "children"), Output("kpi-rate", "children"), Output("kpi-rate-sub", "children"), 
              Output("kpi-med-secs", "children"), Output("kpi-goals", "children"), Output("kpi-goals-sub", "children"), 
              Input("team", "value"), Input("player", "value"), Input("strength", "value"), Input("win-type", "value"))
def update_graphs(team, player, strength, win_type):
    with duckdb.connect(str(DB_PATH), read_only=True) as con2:
        df2 = get_shot_rate_grid(con2, team, player, strength, win_type)
        event_shot_rate = get_shot_rate_by_how_puck_win(con2, team, player, strength)
        player_table_df = get_player_table(con2, team, player, strength, win_type)
        end_reason = get_end_reason_on_win(con2, team, player, strength, win_type)
        summary = get_summary(con2, team, player, strength, win_type)
    
    # rink figure
    fig_rink = build_rink(df2)

    # win type graph
    fig_bar = px.bar(
        event_shot_rate,
        x = "rate",
        y = "win_type",
        orientation="h",
        color_discrete_sequence=["#1F4E8C"],
        custom_data=["wins", "total_goals", "med_seconds_to_shot"]
    )
    fig_bar.update_layout(yaxis={"categoryorder": "trace"}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=80, r=80, t=10, b=0), height=500, bargap=0.55)
    x_max = event_shot_rate["rate"].max() if not event_shot_rate.empty else 1
    fig_bar.update_xaxes(visible=False, title="", range=[0, x_max * 1.5])
    fig_bar.update_yaxes(visible=True, title="")
    fig_bar.update_traces(
       texttemplate="%{x:.1%} · %{customdata[0]} wins",
       hovertemplate="%{y}<br>%{x:.1%} led to a shot<br>%{customdata[0]} wins · %{customdata[1]} goals<br>Median %{customdata[2]}s to shot<extra></extra>",
       textposition="outside", marker_line_width = 0, width=0.45, marker=dict(cornerradius=30)
   )
    
    # end reason graph
    end_reason["Chart"] = ""
    fig_bar_stack = px.bar(
        end_reason,
        y = "Chart",
        x = "totals",
        color = "end_reason",
        orientation="h",
        color_discrete_sequence=["#D97715", "#1D4ED8", "#CBD5E1", "#475569"],
        category_orders={"end_reason": end_reason["end_reason"].tolist()}
    )
    fig_bar_stack.update_layout(yaxis={"categoryorder": "trace"}, xaxis=dict(visible=False),yaxis_title=None, plot_bgcolor="white", 
                                margin=dict(l=20, r=20, t=40, b=100), height=300, bargap=0.55, 
                                legend=dict(orientation="v", yanchor="top", y=0.25, xanchor="left", x=0, title_text=""))
    fig_bar_stack.update_traces(
       marker_line_width = 0, width=0.4, marker=dict(cornerradius=30)
   )
#     #x_max = end_reason["totals"].max() if not end_reason.empty else 1
#     fig_bar_stack.update_xaxes(visible=False, title="",)
#     fig_bar_stack.update_yaxes(visible=False, title="")
#     fig_bar_stack.update_traces(
#        texttemplate="%{y:.1%} · %{customdata[0]} totals",
#        hovertemplate="%{customdata[0]} totals ·rate<extra></extra>",
#        textposition="outside", marker_line_width = 0, width=0.45
#    )
    summary_data = summary
    wins = f"{summary_data.wins:,.0f}"
    wins_sub = f"{summary_data.recoveries:,.0f} recoveries · {summary_data.takeaways:,.0f} takeaways"
    rate = f"{summary_data.rate:.1%}" if pd.notna(summary_data.rate) else "-"
    rate_sub = f"{summary_data.shots:,.0f} of {summary_data.wins:,.0f} wins"
    med_time = f"{summary_data.med_secs:.1f}s" if pd.notna(summary_data.med_secs) else "-"
    goal = f"{summary_data.goals:,.0f}"
    goal_sub = f"{summary_data.rebound_goals:,.0f} of them off rebounds"

    return fig_rink, fig_bar, player_table_df.to_dict('records'), fig_bar_stack, wins, wins_sub, rate, rate_sub, med_time, goal, goal_sub

if __name__ == "__main__":
    app.run(debug=True)