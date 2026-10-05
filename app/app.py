import duckdb
import dash_bootstrap_components as dbc
from dash import Dash, html
from pipeline.config import DB_PATH

with duckdb.connect(str(DB_PATH), read_only=True) as con:
    wins, rate = con.execute(
        "SELECT COUNT(*), AVG(led_to_shot::INT) FROM warehouse.fact_puck_wins"
    ).fetchone()

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server  # what the host runs when deployed

app.layout = dbc.Container([
    html.H1("Forecheck Payoff"),
    html.P(f"{wins:,} offensive-zone puck wins · {rate:.1%} led to a shot within 10s"),
])

if __name__ == "__main__":
    app.run(debug=True)