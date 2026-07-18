from dash import html, dcc, callback, Input, Output, State, dash_table
import dash
import fastf1
import pandas as pd

def lap_time_table():
    layout = html.Div(style={
        'id': 'lap-time-table-container',
        'backgroundColor': '#1a1a1a',
        'borderRadius': '10px',
        'padding': '15px',
        'marginBottom': '20px'
    }, children=[
        html.H3("Fastest Lap Details", style={'color': '#00CED5'}),
        dash_table.DataTable(
            id='lap-time-table',
            columns=[
                {'name': 'Driver', 'id': 'Driver'},
                {'name': 'Lap Time', 'id': 'LapTime'},
                {'name': 'Sector 1', 'id': 'Sector1'},
                {'name': 'Sector 2', 'id': 'Sector2'},
                {'name': 'Sector 3', 'id': 'Sector3'},
            ],
            data=[
                {'Driver': '', 'LapTime': '', 'Sector1': '', 'Sector2': '', 'Sector3': ''}
            ],
            style_cell={'textAlign': 'center', 'color': '#00CED5', 'backgroundColor': '#1a1a1a'},
            style_header={'backgroundColor': '#111111', 'fontWeight': 'bold'},
            style_table={'width': '100%', 'marginTop': '10px'}
        )
    ])

    return layout