import duckdb
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
import rink_plotly.rink_plot as rink_plot
from pipeline.config import DB_PATH
import plotly.graph_objects as go
import pandas as pd
from vizro.figures.library import kpi_card
from app.queries import get_puck_wins, get_shot_rate_grid

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
    df2 = get_shot_rate_grid(con)


app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # what the host runs when deployed
rink_fig = rink_plot.rink(setting='ozone', vertical=False)
rink_fig.update_xaxes(range=[25, 101], constrain='domain')
rink_fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))

wins_kpi = pd.DataFrame({'Total Wins': [wins]})

# First Query to get points on the rink
rink_fig.add_trace(go.Heatmap(
    x=df2["cx"], y=df2["cy"], z=df2["rate"],
    customdata=df2["n"],
    colorscale="Blues", opacity=0.75,
    colorbar=dict(title='Shot Rate', tickformat=".0%"), 
    hovertemplate="%{z:.0%} led to a shot<br>%{customdata} wins<extra></extra>",))

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
    dbc.Row([
        # KPIs
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("OZ puck wins"),
                dbc.CardBody([
                    html.H1(wins),
                    html.P(f"{win_rate_count:.0f} of {wins} wins", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ], style={"width": "18rem"}),
            width="auto"
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Led to a shot within 10s"),
                dbc.CardBody([
                    html.H1(f"{rate:.2%}"),
                    html.P("Placeholder", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ], style={"width": "18rem"}),
            width="auto"
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Median time to shot"),
                dbc.CardBody([
                    html.H1(f"{seconds_to_shot[0]:.1f}s"),
                    html.P("Most shots come fast or not at all", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ], style={"width": "18rem"}),
            width="auto"
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Goals off puck wins"),
                dbc.CardBody([
                    html.H1(goals),
                    html.P(f"{rebound[0]} of them off rebounds", style = {'fontSize': '12px'}, className="card-text"),
                ]),
            ], style={"width": "18rem"}),
            width="auto"
        ),
        ]),
    dcc.Graph(
        id='hockey-rink',
        figure=rink_fig
    )
])

if __name__ == "__main__":
    app.run(debug=True)