import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from app.config import Config
from app.layouts import navbar, upload_layout, dashboard_layout, chat_layout

# Ensure directories exist
Config.ensure_dirs()

# Create app
external_stylesheets = [
    dbc.themes.FLATLY, 
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"
]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True
)
app.title = "TenderGPT (Dash)"
server = app.server

# App layout
app.layout = dbc.Container([
    dcc.Location(id="url", refresh=False),
    navbar(),
    html.Br(),
    dcc.Store(id="tenders-store", data=[]),
    dcc.Store(id="chat-store", data=[]),
    dcc.Interval(id="progress-interval", interval=1*1000, n_intervals=0, disabled=True),
    
    # Pages
    html.Div(id="page-upload", children=upload_layout(), style={"display":"block"}),
    html.Div(id="page-dashboard", children=dashboard_layout(), style={"display":"none"}),
    html.Div(id="page-chat", children=chat_layout(), style={"display":"none"}),
], fluid=True)

# Import callbacks after app is created
from app.callbacks import *

if __name__ == "__main__":
    import webbrowser
    host = "127.0.0.1"
    port = 8050
    url = f"http://{host}:{port}"
    webbrowser.open_new_tab(url)
    app.run(host=host, port=port, debug=True)