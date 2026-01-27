#!/usr/bin/env python3
"""Entry point for TenderGPT application"""
from app.main import app

if __name__ == "__main__":
    app.run_server(debug=True, host="127.0.0.1", port=8050)