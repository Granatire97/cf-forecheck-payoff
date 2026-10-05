import duckdb
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
import rink_plotly.rink_plot as rink_plot
from pipeline.config import DB_PATH
import plotly.graph_objects as go
from app.queries import get_puck_wins

with duckdb.connect(str(DB_PATH), read_only=True) as con:
    wins, rate = con.execute(
        "SELECT COUNT(*), AVG(led_to_shot::INT) FROM warehouse.fact_puck_wins"
    ).fetchone()

    df = get_puck_wins(con)

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # what the host runs when deployed
rink_fig = rink_plot.rink(setting='ozone', vertical=False)
rink_fig.update_xaxes(range=[25, 101], constrain='domain')
rink_fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))

# First Query to get points on the rink
for led, name, color in [(False, "No Shot", "#9AA581"), (True, "Led to shot", "#1F4E8C")]:
    part = df[df['led_to_shot'] == led]
    rink_fig.add_trace(   go.Histogram2d(
       x=df["plot_x"], y=df["plot_y"], z=df["led_to_shot"].astype(int),
       histfunc="avg", # shot rate per cell
       xbins=dict(start=25, end=100, size=15),
       ybins=dict(start=-42.5, end=42.5, size=17),
       colorscale="Blues", opacity=0.75,
   ))


app.layout = dbc.Container([
    html.H1("Forecheck Payoff"),
    html.P(f"{wins:,} offensive-zone puck wins · {rate:.1%} led to a shot within 10s"),
    dcc.Graph(
        id='hockey-rink',
        figure=rink_fig
    )
])

if __name__ == "__main__":
    app.run(debug=True)