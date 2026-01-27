import os
import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

def write_json(path: str, obj: Any):
    """Save object as JSON"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def read_json_safe(path: str) -> Optional[Dict]:
    """Read JSON file safely"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def safe_stem(s: str) -> str:
    """Generate filesystem-safe filename"""
    return re.sub(r'[\\/:\"*?<>|]+', '_', s).strip()

def clean_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Clean metadata for storage"""
    clean_meta = {}
    for k, v in meta.items():
        if v is None:
            clean_meta[k] = ""
        elif isinstance(v, list):
            if all(isinstance(x, (str, int, float, bool)) for x in v):
                clean_meta[k] = ", ".join(map(str, v))
            else:
                clean_meta[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, dict):
            clean_meta[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (str, int, float, bool)):
            clean_meta[k] = v
        else:
            clean_meta[k] = str(v)
    return clean_meta

def save_upload(file_bytes: bytes, filename: str) -> str:
    """Save uploaded file"""
    from app.config import Config
    os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
    upload_path = os.path.join(Config.UPLOADS_DIR, filename)
    with open(upload_path, "wb") as f:
        f.write(file_bytes)
    return upload_path

# Add other utility functions...