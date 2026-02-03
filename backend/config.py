import os
import pandas as pd

# --------------------
# Importing Keys
# --------------------

try:
    keys_df = pd.read_excel(
        r"./AI Keys.xlsx",
        sheet_name="Keys"
    )
    open_ai_key = keys_df[keys_df['Key']=='open_ai_key']['Value'].iloc[0]
    azure_api_key = keys_df[keys_df['Key']=='azure_api_key']['Value'].iloc[0]
    azure_endpoint = keys_df[keys_df['Key']=='azure_endpoint']['Value'].iloc[0]
    azure_api_version = keys_df[keys_df['Key']=='azure_api_version']['Value'].iloc[0]
    azure_deployment_model = keys_df[keys_df['Key']=='azure_deployment_model']['Value'].iloc[0]
    azure_deployment_name = keys_df[keys_df['Key']=='azure_deployment_name']['Value'].iloc[0]
except Exception as e:
    print(f"Warning: Could not load keys from Excel. Using defaults/env vars. Error: {e}")
    open_ai_key = os.getenv("OPENAI_API_KEY", "")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "")
    azure_deployment_model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

# --------------------
# Config Variables
# --------------------
CONFIG = {
    "provider": "azure", #azure/openai
    "openai_api_key": open_ai_key,
    "azure_api_key": azure_api_key,
    "azure_endpoint": azure_endpoint,
    "azure_api_version": azure_api_version,
    "llm_model": azure_deployment_name,
    "llm_temperature": 0.0, #Value from 0-1, lower value gives predictable and stable results, higher value gives random results.
    "llm_max_tokens": 2000,
    "use_llm_extract": True,
    "use_llm_eval": True,
    "use_llm_summary": True,
    "tesseract_cmd": r"C:/Program Files/Tesseract-OCR/tesseract.exe",
    "uploads_dir": "./uploads",
    "extraction_output_dir": "./Outputs/Extractions",
    "FONT_FAMILY": "Inter, sans-serif",
    "progress_file": "./uploads/progress.json",
    "pending_results_file": "./uploads/pending_results.json",
    "debug_logs": True,
    "rag_chunk_chars": 3500,
    "rag_chunk_overlap": 400,
    "rag_top_k": 3,
    "rag_context_chars": 12000,
}
