import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import fastf1
import polars as pl
import os
import dash_bootstrap_components as dbc

## HELPER METHODS

### Enable data chaching to reduce network load
if not os.path.exists('cache'):
    os.makedirs('cache')

fastf1.Cache.enable_cache('cache')

# Fetch the fastest lap



## APPLICATION CODE
app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.CYBORG])


navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dcc.Link('Historic Fastest Lap', href='/historic-fastest-lap', style={'color': '#00CED5', 'fontSize': '18px'})),
    ],
    brand="F1 Telemetry Visualiser",
    brand_href="/",
    color="#111111",
    dark=True,
    fluid=True,
    style={'marginBottom': '20px'}
)

app.layout = html.Div([
    navbar,
    dash.page_container
], style={'backgroundColor': '#111111', 'color': '#00CED5', 'minHeight': '100vh', 'padding': '20px', 'margin': '0px'})


if __name__ == '__main__':
    app.run(debug=True)