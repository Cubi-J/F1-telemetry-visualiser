import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import fastf1
import polars as pl
import os

### Enable data chaching to reduce network load
if not os.path.exists('cache'):
    os.makedirs('cache')

fastf1.Cache.enable_cache('cache')

session = fastf1.get_session(2025, 'Australia', 'R')
session.load()

# Fetch the driver's name, number, and abbreviation
def get_driver_list():

    driver_numbers = session.drivers
    drivers = []
    for num in driver_numbers:
        driver = session.get_driver(num)
        drivers.append({'name': driver['FullName'], 'number': 'num', 'value': driver['Abbreviation']})

    return drivers

# Extract the drivers name and abbreviation for dropdown
def convert_drivers_to_dropdown(drivers):
    options = []
    for driver in drivers:
        options.append({'label': driver['name'], 'value': driver['value']})

    return options

# Fetch the fastest lap
def get_fastest_lap(driver_code):
    laps = session.laps
    fastest_lap = laps.pick_drivers(driver_code).pick_fastest()

    return fastest_lap

# Fetch telemetry for a given lap
def get_telemetry_for_lap(lap):
    telemetry = lap.get_telemetry()
    df = pl.from_pandas(telemetry)

    df = df.with_columns(
        (pl.col("Time").dt.total_nanoseconds() / 1e9).alias("TimeSeconds")
    )
    return df


app = dash.Dash(__name__)

app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#00CED5', 'padding': '20px'},
    children=[
        html.H1("F1 Telemetry", style={'textAlign': 'center', 'color': "#00CED5"}),

        html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
            html.Div([
                html.Label("SELECT DRIVER", style={'color': '#00CED5', 'fontSize': '12px'}),
                dcc.Dropdown(
                    id='driver-dropdown',
                    options=convert_drivers_to_dropdown(get_driver_list()),
                    value='VER',
                    style={'width': '200px', 'color': 'black'}
                ),
            ]),
        ]),
      
        dcc.Graph(
            id='live-telemetry-graph',
            responsive=True,
            figure={
                'data': [],
                'layout': {
                    'title': 'Select a driver to view telemetry',
                    'plot_bgcolor': '#111111',
                    'paper_bgcolor': '#111111',
                    'font': {'color': '#00CED5'},
                    'xaxis': {
                        'gridcolor': '#333', 
                        'title': {'text': 'Distance (m)', 'font': {'color': '#00CED5'}},
                        },
                    'yaxis': {
                        'gridcolor': '#333', 
                        'title': {'text': 'Speed (km/h)', 'font': {'color': '#00CED5'}}
                        }
                }   
            }
        )
    ])



# Update the graph
@app.callback(
    Output('live-telemetry-graph', 'figure'),
    Input('driver-dropdown', 'value')
)
def update_graph(selected_driver):
    print(f"Loading telemetry for: {selected_driver}")

    # Get telemetry
    telemetry = get_telemetry_for_lap(get_fastest_lap(selected_driver))
    if telemetry is None:
        return dash.no_update
    
    trace = go.Scatter(
        x=telemetry['TimeSeconds'],
        y=telemetry['Speed'],
        mode='lines',
        name=f'Speed over Distance - {selected_driver}',
        line={'color': '#00CED5'}
    )

    return {
        'data': [trace],
        'layout': {
            'title': {'text': f'{selected_driver}',
                      'font': {'color': '#00CED5', 'size': 20}
                      },
            'plot_bgcolor': '#111111',
            'paper_bgcolor': '#111111',
            'font': {'color': '#00CED5'},
            'xaxis': {
                'gridcolor': '#333', 
                'title': {'text': 'Distance (m)', 'font': {'color': '#00CED5'}},
                },
            'yaxis': {
                'gridcolor': '#333', 
                'title': {'text': 'Speed (km/h)', 'font': {'color': '#00CED5'}}
                }
        }   
    }

if __name__ == '__main__':
    app.run(debug=True)