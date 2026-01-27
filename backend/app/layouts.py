import dash_bootstrap_components as dbc
from dash import html, dcc

def navbar():
    """Create navigation bar"""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.A(
                    dbc.Row([
                        dbc.Col(html.Img(src="/assets/Logo.png", height="46px"), width="auto"),
                        dbc.Col(dbc.NavbarBrand("MeghaAI", className="ms-2"), 
                               style={"paddingLeft": "6px"})
                    ], align="center", className="g-0"),
                    href="/"
                ), width="auto"),
                dbc.Col(dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Upload", href="/", id="nav-upload")),
                    dbc.NavItem(dbc.NavLink("Dashboard", href="/dashboard", id="nav-dashboard")),
                    dbc.NavItem(dbc.NavLink("Chat", href="/chat", id="nav-chat")),
                ], navbar=True), style={"textAlign":"right"}, width=True)
            ], align="center", className="w-100")
        ]),
        color="#550ea1", dark=True, sticky="top"
    )

def upload_layout():
    """Upload page layout"""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Upload Tenders (PDF/DOCX/TXT)")),
                dbc.CardBody([
                    dcc.Upload(
                        id="upload-files",
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            "width":"100%","height":"120px","lineHeight":"120px",
                            "borderWidth":"1px","borderStyle":"dashed",
                            "borderRadius":"6px","textAlign":"center",
                            "margin-bottom":"10px"
                        },
                        multiple=True
                    ),
                    html.Div(id="upload-output"),
                    html.Br(),
                    dbc.Button("Process Uploaded Files", id="process-btn", color="primary"),
                    html.Br(), html.Br(),
                    dbc.Progress(id="process-progress", value=0, striped=True, 
                                animated=True, style={"height":"18px","display":"none"}),
                    html.Div(id="process-status", className="small text-muted mt-1")
                ])
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Upload Instructions")),
                dbc.CardBody([
                    html.P("Upload PDF/DOCX/TXT tender documents."),
                    html.P("Extraction will run regex + optional LLM extraction."),
                    html.P("LLM extraction/eval uses Azure OpenAI if configured.")
                ])
            ])
        ], md=6)
    ])

def dashboard_layout():
    """Dashboard page layout"""
    return html.Div([
        dbc.Row([
            dbc.Col(html.H3("Tender Dashboard"), md=8),
            dbc.Col(dbc.Button("Refresh KPIs", id="refresh-kpi", color="secondary"), 
                   md=4, style={"textAlign":"right"})
        ]),
        html.Hr(),
        dbc.Row(id="kpi-row"),
        html.Hr(),
        dbc.Row([
            dbc.Col(html.Div(id="tender-tiles"), md=7),
            dbc.Col(html.Div(id="tender-detail-area"), md=5)
        ])
    ])

def chat_layout():
    """Chat page layout"""
    return html.Div([
        html.H3("TenderGPT Chat"),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.Div(id="chat-window", style={
                    "maxHeight":"60vh","overflowY":"auto",
                    "padding":"10px","border":"1px solid #ddd",
                    "borderRadius":"8px"
                }),
                html.Br(),
                dbc.InputGroup([
                    dbc.Input(id="chat-input", placeholder="Ask a question about tenders..."),
                    dbc.Button("Send", id="chat-send", color="primary")
                ])
            ], md=8),
            dbc.Col([
                html.H6("Context selector"),
                html.P("Choose a tender to include in context for the LLM:"),
                dcc.Dropdown(id="chat-context-select", multi=True, 
                           placeholder="Select tenders for context")
            ], md=4)
        ])
    ])