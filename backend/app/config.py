import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # LLM Configuration
    PROVIDER = os.getenv("PROVIDER", "azure")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    AZURE_API_KEY = os.getenv("AZURE_API_KEY")
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-01")
    AZURE_DEPLOYMENT_MODEL = os.getenv("AZURE_DEPLOYMENT_MODEL", "gpt-4")
    AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")
    
    # Processing configuration
    USE_LLM_EXTRACT = True
    USE_LLM_EVAL = True
    USE_LLM_SUMMARY = True
    LLM_TEMPERATURE = 0.0
    LLM_MAX_TOKENS = 1000
    
    # File paths
    UPLOADS_DIR = "./outputs/uploads"
    EXTRACTION_OUTPUT_DIR = "./outputs/extractions"
    PROGRESS_FILE = "./outputs/uploads/progress.json"
    PENDING_RESULTS_FILE = "./outputs/uploads/pending_results.json"
    
    # Text processing
    CHUNK_SIZE = 6000
    CHUNK_OVERLAP = 400
    TESSERACT_CMD = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
    
    # UI
    FONT_FAMILY = "Inter, sans-serif"
    DEBUG_LOGS = True
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {k: v for k, v in cls.__dict__.items() 
                if not k.startswith('_') and not callable(v)}
    
    @classmethod
    def ensure_dirs(cls):
        """Create necessary directories"""
        os.makedirs(cls.UPLOADS_DIR, exist_ok=True)
        os.makedirs(cls.EXTRACTION_OUTPUT_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(cls.PROGRESS_FILE), exist_ok=True)