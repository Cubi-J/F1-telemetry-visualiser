import dash
from dash import callback, dcc, html, Input, Output, State, dash_table
from components.year_event_driver_dropdown import year_event_driver_dropdown
from components.lap_time_table import lap_time_table
from utils.fast_f1_handler import fetch_historic_fastest_lap_data
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
import os


dash.register_page(__name__, path='/historic-fastest-lap')

layout = html.Div(style={
    'backgroundColor': '#111111', 'color': '#00CED5', 'padding': '20px'
}, children=[
    dcc.Store(id='session-store'),
    year_event_driver_dropdown(),
        
    dcc.Loading(
        id="loading-telemetry",
        type="graph",
        children=(
            lap_time_table(),  # updated via callback
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
                    }   
                }
            ),
        ),
    ),
])
        

# Update the graph
@callback(
    Output('live-telemetry-graph', 'figure'),
    Output('lap-time-table', 'data'),
    Input('session-store', 'data'),
)
def update_graph(session_info):
    
    if not session_info:
        return dash.no_update
    else:
        data = fetch_historic_fastest_lap_data(session_info)
    
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1,  
        row_heights=[0.5, 0.25, 0.25]
    )

    lap_time_data = []
        
    for driver in data.keys():
        telemetry = data[driver]['telemetry']
        line_config = data[driver]['line_config']

        lap_time_data.append({
            'Driver': driver,
            'LapTime': data[driver]['timing_data']['LapTime'],
            'Sector1': data[driver]['timing_data']['Sector1'],
            'Sector2': data[driver]['timing_data']['Sector2'],
            'Sector3': data[driver]['timing_data']['Sector3'],
        })

        # Speed line 
        fig.add_trace(go.Scatter(
            x=telemetry['Distance'],
            y=telemetry['Speed'],
            name=f'Speed - {driver}',
            line=line_config,
            legendgroup=driver,
        ), row=1, col=1)

        # Throttle line
        fig.add_trace(go.Scatter(
            x=telemetry['Distance'],
            y=telemetry['Throttle'],
            name=f'Throttle - {driver}',
            line=line_config,
            legendgroup=driver,
            showlegend=False,
        ), row=2, col=1)

        # Brake line
        fig.add_trace(go.Scatter(
            x=telemetry['Distance'],
            y=telemetry['Brake'],
            name=f'Brake - {driver}',
            line=line_config,
            legendgroup=driver,
            showlegend=False,
        ), row=3, col=1)

    fig.update_layout(
            title=f"Fastest Lap Telemetry",
            template="plotly_dark",
            plot_bgcolor='#111111',
            paper_bgcolor='#111111',
            yaxis_title="Speed (kn/h)"
        )

    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1, gridcolor='#333')
    fig.update_yaxes(title_text="Throttle (%)", row=2, col=1, gridcolor='#333', range=[-5, 105])
    fig.update_yaxes(title_text="Brake (on/off)", row=3, col=1, gridcolor='#333', range=[0, 1])
    
    # Only label the bottom X-axis since they share data
    fig.update_xaxes(title_text="Distance (m)", row=3, col=1, gridcolor='#333')

    return fig, lap_time_data