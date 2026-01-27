from dash import Input, Output, State, ctx, ALL, html, dcc, dash
import dash_bootstrap_components as dbc
import json
import threading
import os
from typing import List, Dict, Any

from app.config import Config
from core.processor import FileProcessor
from core.vector_store import ChromaVectorStore
from core.utils import read_json_safe

# Initialize components
processor = FileProcessor()
vector_store = ChromaVectorStore()

# Define callbacks
def register_callbacks(app):
    """Register all Dash callbacks"""
    
    @app.callback(
        Output("page-upload", "style"),
        Output("page-dashboard", "style"),
        Output("page-chat", "style"),
        Input("url", "pathname")
    )
    def toggle_pages(pathname):
        if pathname is None or pathname == "/":
            return {"display":"block"}, {"display":"none"}, {"display":"none"}
        if pathname == "/dashboard":
            return {"display":"none"}, {"display":"block"}, {"display":"none"}
        if pathname == "/chat":
            return {"display":"none"}, {"display":"none"}, {"display":"block"}
        return {"display":"block"}, {"display":"none"}, {"display":"none"}
    
    @app.callback(
        Output("upload-output", "children"),
        Output("process-progress", "style"),
        Output("process-progress", "value"),
        Output("process-progress", "children"),
        Output("process-status", "children"),
        Output("progress-interval", "disabled"),
        Output("tenders-store", "data"),
        Input("upload-files", "contents"),
        Input("upload-files", "filename"),
        Input("process-btn", "n_clicks"),
        Input("progress-interval", "n_intervals"),
        State("tenders-store", "data")
    )
    def combined_upload_and_poll(contents, filenames, process_clicks, n_intervals, tenders_data):
        """Handle file upload and processing progress"""
        tenders_data = tenders_data or []
        trig = ctx.triggered_id
        
        if trig == "upload-files":
            if not filenames:
                return html.Div("No files selected."), {"display":"none"}, 0, "", "", True, tenders_data
            
            preview = html.Div([
                html.Div("Files selected:", className="mb-2"),
                html.Ul([html.Li(name) for name in filenames]),
                html.Div("Click 'Process Uploaded Files' to extract and save.", 
                        className="text-muted small mt-2")
            ])
            return preview, {"display":"none"}, 0, "", "", True, tenders_data
        
        if trig == "process-btn":
            if not contents or not filenames:
                alert = dbc.Alert("No files to process. Please select files first.", 
                                color="warning")
                return alert, {"display":"none"}, 0, "", "", True, tenders_data
            
            encoded_items = [{"content": c, "filename": n} for c, n in zip(contents, filenames)]
            
            # Start background thread
            thr = threading.Thread(
                target=processor.process_files,
                args=(encoded_items,),
                daemon=True
            )
            thr.start()
            
            preview = dbc.Alert([
                html.Div(f"Processing {len(encoded_items)} files in background:", 
                        style={"fontWeight":"600"}),
                html.Ul([html.Li(n) for n in filenames])
            ], color="info")
            
            return preview, {"display":"block"}, 0, f"0/{len(encoded_items)}", "Processing started...", False, tenders_data
        
        if trig == "progress-interval":
            prog = read_json_safe(Config.PROGRESS_FILE) or {}
            if not prog:
                return dash.no_update, {"display":"none"}, 0, "", "Idle", True, tenders_data
            
            total = int(prog.get("total", 0) or 0)
            done = int(prog.get("done", 0) or 0)
            status = prog.get("status", "")
            current = prog.get("current_file", "")
            pct = int(done * 100 / total) if total > 0 else 0
            children = f"{done}/{total}"
            
            if status in ("running", "queued"):
                status_text = f"Processing: {current}" if current else "Processing..."
                return dash.no_update, {"display":"block"}, pct, children, status_text, False, tenders_data
            
            if status == "done":
                pending = read_json_safe(Config.PENDING_RESULTS_FILE) or {}
                results = pending.get("results", []) if pending else []
                existing = list(tenders_data)
                
                for r in results:
                    sf = r.get("source_file")
                    if not any((e.get("source_file") and e.get("source_file") == sf) 
                              for e in existing):
                        existing.append(r)
                
                # Clean up progress files
                try:
                    os.remove(Config.PROGRESS_FILE)
                    os.remove(Config.PENDING_RESULTS_FILE)
                except:
                    pass
                
                return dash.no_update, {"display":"none"}, 100, f"{done}/{total}", "Processing complete.", True, existing
            
            if status == "error":
                return dash.no_update, {"display":"none"}, pct, children, "Error during processing.", True, tenders_data
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, tenders_data
    
    # Add other callbacks for dashboard, chat, etc.
    # ...

# Register callbacks when module is imported
register_callbacks(app)