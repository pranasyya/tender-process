# --------------------
# Imports
# --------------------
import pdfplumber
import os
import io
import re
import json
import tempfile
import base64
import threading
import webbrowser
import time
from typing import Any, Dict, List, Tuple
from datetime import datetime, date
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer  

# Pdf Reader
try:
    import pymupdf as fitz  
except Exception:
    fitz = None

from PIL import Image
import pytesseract
import docx2txt

# Import OpenAI/Azure Client
try:
    from openai import OpenAI, AzureOpenAI
except Exception:
    OpenAI = None
    AzureOpenAI = None


# --------------------
# Importing Keys
# --------------------

keys_df = pd.read_excel(
    r"C:\Users\Pranasyya\Downloads\Tender\Tender\backend\AI Keys.xlsx",
    sheet_name="Keys"
)


open_ai_key = keys_df[keys_df['Key']=='open_ai_key']['Value'].iloc[0]
azure_api_key = keys_df[keys_df['Key']=='azure_api_key']['Value'].iloc[0]
azure_endpoint = keys_df[keys_df['Key']=='azure_endpoint']['Value'].iloc[0]
azure_api_version = keys_df[keys_df['Key']=='azure_api_version']['Value'].iloc[0]
azure_deployment_model = keys_df[keys_df['Key']=='azure_deployment_model']['Value'].iloc[0]
azure_deployment_name = keys_df[keys_df['Key']=='azure_deployment_name']['Value'].iloc[0]

# ===============================
# TENDER ANALYSIS FUNCTIONS
# ===============================

def extract_text(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print("PDF read error:", e)
    return text


def extract_emd(text):
    pattern = r"(EMD|Earnest Money Deposit).*?(₹|Rs\.?)\s?([\d,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(3).replace(",", ""))
    return 0


def calculate_confidence(text):
    score = 0
    t = text.lower()

    if "security audit" in t:
        score += 30
    if "iso 27001" in t:
        score += 20
    if "experience" in t:
        score += 10
    if "government" in t:
        score += 10
    if "emd" in t:
        score += 10

    return min(score, 100)


def classify_tender(confidence):
    if confidence >= 70:
        return "Recommended to Bid"
    elif confidence >= 40:
        return "Needs Review"
    return "No-Bid"



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
    "llm_max_tokens": 1000,
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
}

if CONFIG.get("tesseract_cmd"):
    pytesseract.pytesseract.tesseract_cmd = CONFIG["tesseract_cmd"]

# --------------------
# Assets and CSS file
# --------------------
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

assets_dir = os.path.join(BASE_DIR, "assets")
os.makedirs(assets_dir, exist_ok=True)

css_path = os.path.join(assets_dir, "custom.css")

font_family = CONFIG.get("FONT_FAMILY", "Arial")

css_text = f"""
body {{
    font-family: {font_family};
}}
"""

with open(css_path, "w", encoding="utf-8") as _f:
    _f.write(css_text)


os.makedirs(CONFIG.get("uploads_dir", "./uploads"), exist_ok=True)
progress_dir = os.path.dirname(CONFIG.get("progress_file", "./uploads/progress.json")) or CONFIG.get("uploads_dir", "./uploads")
pending_dir = os.path.dirname(CONFIG.get("pending_results_file", "./uploads/pending_results.json")) or CONFIG.get("uploads_dir", "./uploads")
os.makedirs(progress_dir, exist_ok=True)
os.makedirs(pending_dir, exist_ok=True)
os.makedirs(CONFIG.get("extraction_output_dir", "./Outputs/Extractions"), exist_ok=True)


# --------------------
# Prompts
# --------------------
LLM_PROMPT_TEMPLATE = r"""
You are an information extraction system. Read the TEXT and return exactly ONE JSON object following SCHEMA.
Use GLOBAL_HEADER as context if the header appears only once in the document.

SCHEMA = {{
  "tender_id": "",
  "category": "",
  "title": "",
  "location": "",
  "issuing_authority": "",
  "publication_date": "",
  "submission_deadline": "",
  "bid_opening_date": "",
  "bid_opening_time": "",
  "emd": "",
  "tender_fee": "",
  "performance_guarantee": "",
  "contract_duration": "",
  "contact_emails": [],
  "contact_phones": [],
  "scope_of_work": "",
  "eligibility_summary": "",
  "required_documents": "",
  "exclusion_criteria": "",
  "disqualification_criteria": "",
  "technical_documents": "",
  "deliverables": "",
  "projects": [],
  "bidding_scope": "",
  "short_summary": ""
}}

GLOBAL_HEADER (if provided):
{global_header}

TEXT (Page/Chunk = {page_reference}):
{chunk_text}

STRICT RULES (apply to every field):
- If the field is not explicitly present, output "N/A" for strings and [] for arrays. DO NOT invent values.
- Dates MUST be "DD-MM-YYYY". If you cannot form a valid date, output "N/A".
- Times MUST be "HH:MM AM/PM" (e.g., "03:00 PM"). Else "N/A".
- Monetary fields (EMD, Tender Fee) MUST be concise values ONLY (e.g., "₹ 70,000", "Rs. 1,000", "2%"). No sentences.
- Performance Guarantee: ONLY a percent or an amount (e.g., "5%" or "₹ 1,00,000"). No sentences.
- Contract Duration: concise value ONLY (e.g., "120 days", "2 Years"). No sentences.
- Issuing Authority: organization name ONLY (no bullets, no address, no policy headers like MSME/Make in India/GeM).
- Contact Emails/Phones: arrays of items; no labels like "Cell" or "Ph".
- Category: choose the best-fit from this list only: {categories}
- Scope of Work: short, no more than 6 lines (≈400 chars), concise.
- Short Summary: 3–4 short lines (<100 words) — no repetition, no marketing.
- Projects: if multiple distinct sub-projects appear, list them briefly (each entry as a short string); else [].
- Bidding Scope: single sentence; if absent, "N/A".

CRITICAL EXTRACTION RULES FOR KEY FIELDS:
- tender_id: Look for "Tender ID", "Tender No", "Tender Ref", "NIT No", "RFQ No", "e-Tender ID". Must be alphanumeric code. Never leave blank if found.
- publication_date: FIRST mention of tender date, bid calling date, issue date, or advertised date. Format exactly DD-MM-YYYY.
- short_summary: Concise overview of tender scope, work type, and deliverables. 3-4 sentences max, under 100 words. Ignore marketing language.

OUTPUT FORMAT:
- Return JSON only. No markdown, no commentary, no trailing text.
"""


EVAL_PROMPT = """
You are a business analyst. Based on the tender details below, assign:
- priority_score (1-10)
- pursue_recommendation (PURSUE / DO NOT PURSUE)
Provide concise reasoning.

Tender JSON:
{tender_json}
"""

# --------------------
# Logging helper
# --------------------
def log(msg: str):
    '''
    To check output on terminal, logger.
    '''
    if CONFIG.get("debug_logs"):
        print(f"[Extractor] {msg}")

# --------------------
# Category + Icons
# --------------------
ICON_STYLE_MAP = {
    "Water Treatment": {"emoji": "💧", "color": "#0ea5e9"},
    "Wastewater Treatment": {"emoji": "♻️", "color": "#16a34a"},
    "Power Transmission": {"emoji": "⚡", "color": "#f59e0b"},
    "IT / Software": {"emoji": "💻", "color": "#6366f1"},
    "Consulting": {"emoji": "🧾", "color": "#ef4444"},
    "Aerospace": {"emoji": "🛩️", "color": "#8b5cf6"},
    "Audio": {"emoji": "🎧", "color": "#0ea5e9"},
    "Construction": {"emoji": "🏗️", "color": "#f97316"},
    "Educational Services": {"emoji": "🎓", "color": "#06b6d4"},
    "Radioactive": {"emoji": "☢️", "color": "#f43f5e"},
    "Repair": {"emoji": "🔧", "color": "#94a3b8"},
    "Telecom": {"emoji": "📡", "color": "#fb923c"},
    "Telephone": {"emoji": "☎️", "color": "#fb7185"},
    "Waterworks": {"emoji": "🚰", "color": "#0ea5e9"},
    "Web Development": {"emoji": "🕸️", "color": "#7c3aed"},
    "Cybersecurity": {"emoji": "🛡️", "color": "#64748b"},
    "Elevators / Lift": {"emoji": "🛗", "color": "#7c3aed"},
}

KEYWORDS_TO_CATEGORY = {
    "elevator": "Elevators / Lift", "lift": "Elevators / Lift",
    "construct": "Construction", "civil": "Construction", "building": "Construction",
    "website": "Web Development", "web portal": "Web Development", "portal": "Web Development",
    "software": "IT / Software", "it ": "IT / Software", "application": "IT / Software",
    "vapt": "Cybersecurity", "security audit": "Cybersecurity", "safe to host": "Cybersecurity", "cert-in": "Cybersecurity",
    "water": "Water Treatment", "effluent": "Wastewater Treatment", "wastewater": "Wastewater Treatment",
    "power": "Power Transmission", "transmission": "Power Transmission",
    "education": "Educational Services", "school": "Educational Services",
    "audio": "Audio", "speaker": "Audio",
    "telecom": "Telecom", "telephone": "Telephone", "phone": "Telephone",
    "nuclear": "Radioactive", "radioactive": "Radioactive",
    "repair": "Repair", "maintenance": "Repair",
}

def detect_category(title: str, scope: str, existing: str = "") -> str:
    """
    Detects the most probable category/sector of a tender
    based on its title or scope text.

    Args:
        title (str): Tender title text.
        scope (str): Short project scope or description.
        existing (str): Pre-existing category (if already detected).

    Returns:
        str: Category label such as 'Water Treatment', 'Power Transmission', etc.
    """
    if existing:
        return existing
    combined = f"{title or ''} {scope or ''}".lower()
    for kw, cat in KEYWORDS_TO_CATEGORY.items():
        if kw in combined:
            return cat
    return existing or ""


# --------------------
# Selecting Icons according to sector
# --------------------
def sector_icon(category_or_sector: str, title: str = "", scope: str = ""):
    """
    Maps each category to an icon file.

    Args:
        category (str): Category name detected from tender.
    Returns:
        str: Path to icon image (PNG/SVG).
    """

    combined = " ".join(filter(None, [str(category_or_sector), title, scope])).lower()

    # try keyword mapping first
    for kw, cat in KEYWORDS_TO_CATEGORY.items():
        if kw in combined:
            m = ICON_STYLE_MAP.get(cat)
            if m:
                return html.Span(m["emoji"], title=cat, style={"fontSize":"20px","display":"inline-block","width":"28px","textAlign":"center"})
    # fallback direct
    if category_or_sector:
        m = ICON_STYLE_MAP.get(category_or_sector)
        if m:
            return html.Span(m["emoji"], title=category_or_sector, style={"fontSize":"20px","display":"inline-block","width":"28px","textAlign":"center"})
    return html.Span("📁", title="Other", style={"fontSize":"20px","display":"inline-block","width":"28px","textAlign":"center"})

ICON_MAP = {k.lower(): v["emoji"] for k, v in ICON_STYLE_MAP.items()}

def pick_icon(category: str, title: str = "", scope: str = ""):
    """
    Fallback helper to select a default icon.
    """
    combined = " ".join(filter(None, [str(category), title, scope])).lower()
    for kw, cat in KEYWORDS_TO_CATEGORY.items():
        if kw in combined:
            return ICON_MAP.get(cat.lower(), "📁")
    if category and category.lower() in ICON_MAP:
        return ICON_MAP[category.lower()]
    return "📁"

# --------------------
# Utility helpers
# --------------------
def write_json(path: str, obj: Any):
    """
    Save a Python dictionary to disk as formatted JSON.

    Args:
        path (str): Output file path (including directory).
        obj (dict): Python object to save.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def safe_stem(s: str) -> str:
    """
    Generate a filesystem-safe filename.

    Args:
        filename (str): Original file name.

    Returns:
        str: Clean version safe for folders.
    """
    return re.sub(r'[\\/:\"*?<>|]+', '_', s).strip()


def clean_metadata(meta: dict) -> dict:
    """
    Sanitize and normalize tender metadata values for JSON serialization and display.

    This function ensures all metadata fields are converted into standardized, 
    display-safe formats — converting complex data types (lists, dicts, None, etc.)
    into readable strings. It helps maintain consistency across the dashboard and 
    avoids serialization errors when saving or displaying extracted tender data.

    Args:
        meta (dict): Raw metadata dictionary possibly containing mixed data types.

    Returns:
        dict: Cleaned metadata dictionary where all values are strings or basic types 
        (str, int, float, bool) suitable for JSON export and UI rendering.
    """
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

# Basic text cleaning
CLEAN_LINE_PATTERNS = [
    re.compile(r"^\s*\d+\s*\|\s*P\s*a\s*g\s*e.*$", re.I),  
]

def build_global_header(full_text: str) -> dict:
    """Extract small, stable header facts from the first ~2 pages to reuse as context."""
    head = full_text[:6000]
    out = {}
    # Title
    m = re.search(r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)", head)
    if m: out["title"] = m.group(1).strip()
    # Issuing authority
    m = re.search(r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)", head)
    if m: out["issuing_authority"] = re.split(r"\n|,? *Address", m.group(1).strip())[0]
    # Publication date
    m = re.search(r"(?i)\b(?:Bid\s*calling|Publication\s*Date|Date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", head)
    if m: out["publication_date"] = sanitize_date_like(m.group(1))
    # Location 
    m = re.search(r"(?i)\b([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*,\s*India)\b", head)
    if m: out["location"] = m.group(1).strip()
    return out

def postprocess_llm_json(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce formats and 'N/A' where appropriate.
    Standardize and sanitize raw LLM-extracted tender data into consistent formats.

    This function enforces clean output after the LLM extraction stage by normalizing
    date and money fields, trimming verbose text, validating contact arrays, 
    and replacing invalid or missing values with "N/A". It ensures the metadata 
    adheres to display-safe and machine-readable constraints for dashboards.

    Args:
        d (dict): Raw tender metadata as returned from the LLM extraction or merge phase.

    Returns:
        dict: Cleaned and standardized metadata dictionary ready for storage,
        evaluation, and dashboard rendering.
    """
    out = dict(d or {})
    # Normalize dates
    for k in ("publication_date","submission_deadline","bid_opening_date"):
        v = out.get(k, "")
        out[k] = sanitize_date_like(v) or ("N/A" if v else "N/A")
    # Time
    t = out.get("bid_opening_time","").strip()
    mt = re.match(r"(?i)^\s*(\d{1,2})[:.](\d{2})\s*(AM|PM)?\s*$", t)
    out["bid_opening_time"] = (f"{int(mt.group(1)):02d}:{mt.group(2)} {mt.group(3) or 'PM'}".upper()
                               if mt else ("N/A" if t else "N/A"))
    # Money fields: require digits; else N/A
    for k in ("emd","tender_fee","performance_guarantee","tender_value"):
        v = sanitize_amount_text(out.get(k,""))
        out[k] = v if (v and re.search(r"\d", v)) else "N/A"
    # Duration: trim to concise token (no sentences)
    dur = out.get("contract_duration","").strip()
    if dur and len(dur) > 40:  # too wordy → extract simple token if present
        m = re.search(r"(?i)\b(\d+\s*(?:day|days|week|weeks|month|months|year|years))\b", dur)
        out["contract_duration"] = m.group(1) if m else "N/A"
    elif not dur:
        out["contract_duration"] = "N/A"
    # Issuing authority: must contain letters; ban known policy words
    ia = out.get("issuing_authority","").strip()
    if (not re.search(r"[A-Za-z]", ia)) or any(w in ia.lower() for w in ["msme","mse procurement","public procurement","make in india","gem"]):
        out["issuing_authority"] = "N/A"
    # Arrays: dedupe + validate
    out["contact_emails"] = emails_cleanup(out.get("contact_emails") if isinstance(out.get("contact_emails"), list) else [])
    out["contact_phones"] = phones_cleanup(out.get("contact_phones") if isinstance(out.get("contact_phones"), list) else [])
    # Category: keep within allowed set or leave blank (we auto-detect later)
    cats = set(ICON_STYLE_MAP.keys())
    if out.get("category") not in cats:
        out["category"] = ""
    # Scope/summary length caps to avoid walls of text
    for k, limit in (("scope_of_work", 500), ("short_summary", 400), ("eligibility_summary", 600), ("required_documents", 600)):
        v = (out.get(k) or "").strip()
        out[k] = v[:limit]
    return out



def clean_text(text: str) -> str:
    """
    Remove noise, normalize spacing, and prepare raw text for extraction.

    This function cleans extracted text by removing common header/footer patterns,
    fixing broken words across line breaks, and normalizing whitespace. It also
    strips unwanted prefixes (like 'mailto:' or 'file://') while retaining 
    meaningful content such as emails or tender details.

    Args:
        text (str): Raw text extracted from PDF or document files.

    Returns:
        str: Cleaned and normalized text string suitable for regex or LLM parsing.
    """
    if not text:
        return text
    # remove headers/footers noise
    lines = text.splitlines()
    kept = []
    for ln in lines:
        drop = False
        for pat in CLEAN_LINE_PATTERNS:
            if pat.search(ln):
                drop = True
                break
        if drop:
            continue
        kept.append(ln)
    s = "\n".join(kept)
    # de-hyphenate simple splits at line breaks
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    # normalize spaces
    s = re.sub(r"[ \t]+", " ", s)
    # keep emails but drop 'mailto:' and 'file://' prefixes
    s = s.replace("mailto:", "").replace("Mailto:", "")
    s = s.replace("file://", "")
    return s


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from PDF, DOCX, or TXT documents.

    Uses:
    - PyMuPDF (fitz) for textual PDFs
    - pytesseract for OCR on scanned PDFs
    - docx2txt for Word files

    Args:
        file_bytes (bytes): Binary content of file.
        filename (str): Original filename for detection.

    Returns:
        str: Extracted text.
    """
    name = filename.lower()
    text = ""
    if name.endswith(".pdf") and fitz is not None:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                ptext = page.get_text("text").strip()
                if ptext and len(ptext) >= 15:
                    text += ptext + "\n"
                else:
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_bytes))
                    text += pytesseract.image_to_string(image, lang="eng") + "\n"
            doc.close()
        except Exception as e:
            print("PDF extraction failed:", e)
            text = ""
    elif name.endswith(".docx") or name.endswith(".doc"):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                text = docx2txt.process(tmp.name) or ""
        except Exception as e:
            print("DOCX extract failed:", e)
            text = ""
    else:
        try:
            text = file_bytes.decode(errors="ignore")
        except Exception:
            text = ""
            print("=== DEBUG: RAW EXTRACTED TEXT ===")
            print("LENGTH:", len(text))
            print("SAMPLE:", text[:500])
            print("================================")

    return clean_text(text)


# --- Improved regex patterns ---
REGEX_PATTERNS = {
    # tender id: prefer slashy codes / masthead refs
    "tender_id": r"(?im)\b(?:Tender\s*(?:Ref\.?|No\.?)|NIT\s*No\.?|e-?Tender\s*(?:No\.|ID)|RFQ\s*No\.?|Tender\s*Document\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{4,})",
    "title": r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)",
    "issuing_authority": r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)",
    "publication_date": r"(?i)\b(?:Bid\s*calling|Publication\s*Date|Date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "submission_deadline": r"(?i)(?:Last\s*Date\s*(?:of)?\s*(?:Submission|Bid\s*Submission|Receipt)|Bid\s*Closing)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "bid_opening_date": r"(?i)\b(?:Bid\s*opening|Opening\s*Date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "bid_opening_time": r"(?i)\b(?:Opening\s*Time|Time)\s*[:\-]?\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:AM|PM)?)",
    # amounts (capture only the value-ish part; we will sanitize later)
    "emd": r"(?i)\b(?:EMD(?:\s*Amount)?|Earnest\s*Money(?:\s*Deposit)?)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",
    "tender_fee": r"(?i)\b(?:Bid\s*Document\s*Fee|Tender\s*Fee|Document\s*Fee)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",
    "performance_guarantee": r"(?i)\b(?:Performance\s*(?:Security|Guarantee))\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,60})",
    "contract_duration": r"(?i)\b(?:Contract\s*Duration|Period\s*of\s*Completion|Duration)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,60})",
    "contact_emails": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "contact_phones": r"(?:(?:\+91[-\s]?)?[\(]?\d{3,5}[\)]?[-\s]?\d{5,8}|\b\d{10}\b)",
    "tender_value": r"(?i)\b(?:Estimated\s*Cost|Tender\s*Value|Project\s*Cost|Approx\.?\s*Value)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",

}


BANNED_SNIPPETS = [
    "msme", "mse procurement", "public procurement", "make in india", "gem", "physical form",
    "drawn in favour", "bank", "ifsc", "dd/", "bg", "cheque", "demand draft",
    "annexure", "refundable", "to be notified later", "of receiving queries",
    "form of dd", "form of bg", "submitted along with", "covering letter"
]





def regex_extract(text: str) -> Dict[str, Any]:
    """
    Robust regex extraction with priority handling for Tender ID and Dates.
    Works for multiline text and multiple date formats.
    """
    extracted = {}

    # ---------- Priority: Tender ID ----------
    tender_id_patterns = [
        r"Tender\s*(?:Ref\.?|ID|No\.?|Reference|Number)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        r"NIT\s*No\.?\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        r"e-?Tender\s*(?:No\.|ID|Reference)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        r"Bid\s*(?:No\.|ID|Reference)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        r"RFQ\s*No\.?\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
    ]

    for pat in tender_id_patterns:
        m = re.search(pat, text, re.I | re.S)  # <-- Added re.S for multiline
        if m:
            tender_id_candidate = m.group(1).strip()
            if len(tender_id_candidate) >= 3 and tender_id_candidate.upper() != "N/A":
                extracted["tender_id"] = tender_id_candidate
                break

    # Fallback generic tender ID if nothing found
    if "tender_id" not in extracted:
        fallback = re.findall(r"\b[A-Z]{2,}-\d+\b", text)
        if fallback:
            extracted["tender_id"] = fallback[0]

    # ---------- Priority: Publication Date ----------
    date_label_patterns = [
        # Explicit labels
        r"(?:Publication\s*Date|Bid\s*Calling\s*Date|Date\s*of\s*Issue|Advertised\s*Date)\s*[:\-]?\s*([0-3]?\d[./-][0-1]?\d[./-]\d{2,4})",
        # Generic numeric date
        r"\b([0-3]?\d[./-][0-1]?\d[./-]\d{2,4})\b",
        # Textual month date e.g., 19 Jan 2026
        r"\b([0-3]?\d\s*(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\s*\d{4})\b"
    ]

    for pat in date_label_patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            date_str = m.group(1).strip()
            extracted["publication_date"] = date_str
            break

    # ---------- Generic regex fields ----------
    if "REGEX_PATTERNS" in globals():
        for field, pattern in REGEX_PATTERNS.items():
            if field in extracted:
                continue
            if field in ["contact_emails", "contact_phones"]:
                matches = re.findall(pattern, text, flags=re.I)
                extracted[field] = list(dict.fromkeys(m.strip() for m in matches if m and m.strip()))
            else:
                m = re.search(pattern, text, flags=re.I | re.S)
                extracted[field] = m.group(1).strip() if m else ""

    return extracted



# --- Sanitizers & validators ---
def sanitize_amount_text(val: str) -> str:
    
    if not val:
        return ""
    s = " ".join(val.strip().split())
    # If contains any banned snippet, likely instruction; return empty to force LLM fallback
    for b in BANNED_SNIPPETS:
        if b in s.lower():
            return ""
    # Try to pick ₹/Rs + number + unit or pure percent
    m_pct = re.search(r"(?i)\b(\d{1,3}(?:\.\d{1,2})?)\s*%(\b|$)", s)
    if m_pct:
        return f"{m_pct.group(1)}%"
    m_amt = re.search(r"(?i)(₹|rs\.?|rupees)\s*([0-9][\d,\.]*)\s*(lacks?|lakhs?|lacs?|crores?)?", s)
    if m_amt:
        cur = "₹" if m_amt.group(1).lower().startswith("₹") else "Rs."
        num = m_amt.group(2)
        unit = m_amt.group(3) or ""
        unit = unit.capitalize() if unit else ""
        return f"{cur} {num}{(' ' + unit) if unit else ''}"
    # Fallback: if there are digits, keep up to first sentence end
    if re.search(r"\d", s):
        s = re.split(r"[.;]", s)[0]
        # Avoid extremely long strings
        if len(s) > 60:
            s = s[:60].rstrip()
        return s
    return ""


def regex_value_valid(field: str, value: str) -> bool:
    
    if not value or not str(value).strip():
        return False
    s = str(value).strip()
    if len(s) > 120 or s.count("\n") > 1:
        return False
    low = s.lower()
    if field in ("emd", "tender_fee", "performance_guarantee"):
        if not re.search(r"\d", s):
            return False
        for b in BANNED_SNIPPETS:
            if b in low:
                return False
    if field == "issuing_authority":
        # must contain letters and not be just punctuation/bullets
        if not re.search(r"[A-Za-z]", s):
            return False
        if re.fullmatch(r"[-–—•\s]+", s):
            return False
        for b in ["public procurement", "msme", "mse procurement", "make in india", "gem"]:
            if b in low:
                return False
    return True


def emails_cleanup(emails: List[str]) -> List[str]:
    clean = []
    for e in emails or []:
        e = e.strip()
        # remove trailing words like "Cell", "Ph", etc.
        e = re.sub(r"(Cell|Ph|Tel|Phone)\b.*$", "", e, flags=re.I).strip()
        # strict email match
        m = re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", e)
        if m and e not in clean:
            clean.append(e)
    return clean


def phones_cleanup(phones: List[str]) -> List[str]:
    HELPLINE_PREFIXES = ("+91", "0", "022", "012", "1800", "1860")

    # normalize Indian numbers; drop obvious bank/account-like sequences (handled by lack of labels here)
    out = []
    for p in phones or []:
        digits = re.sub(r"\D", "", p)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if digits.startswith("0") and len(digits) in (11,12):
            digits = digits.lstrip("0")
        # drop known helpline/IVR prefixes
        if digits.startswith(HELPLINE_PREFIXES):
            continue
        if 8 <= len(digits) <= 10:
            if digits not in out:
                out.append(digits)
    return out

# --------------------
# Build LLM Client
# --------------------
def build_client():
    """
    Creates an LLM client (Azure or OpenAI) based on CONFIG["provider"].

    """
    if CONFIG["provider"] == "azure" and AzureOpenAI is not None:
        try:
            return AzureOpenAI(api_key=CONFIG["azure_api_key"], api_version=CONFIG["azure_api_version"], azure_endpoint=CONFIG["azure_endpoint"])
        except Exception as e:
            print("Azure client build failed:", e)
            return None
    elif CONFIG.get("provider") == "openai" and OpenAI is not None:
        try:
            return OpenAI(api_key=CONFIG["openai_api_key"])
        except Exception as e:
            print("OpenAI client build failed:", e)
            return None
    return None

LLM_CLIENT = build_client()

# --------------------
# LLM Extraction
# --------------------
def llm_extract_chunk(chunk_text: str, page_reference: str = "all", categories: List[str] = None, global_header: dict = None) -> Dict[str, Any]:
    if LLM_CLIENT is None or not CONFIG["use_llm_extract"]:
        return {}
    try:
        cats = categories or list(ICON_STYLE_MAP.keys())
        prompt = LLM_PROMPT_TEMPLATE.format(
            chunk_text=chunk_text[:15000],
            categories=cats,
            page_reference=page_reference,
            global_header=json.dumps(global_header or {}, ensure_ascii=False)
        )
        resp = LLM_CLIENT.chat.completions.create(
            model=CONFIG["llm_model"],
            messages=[{"role":"user","content": prompt}],
            temperature=CONFIG["llm_temperature"],
            max_tokens=CONFIG["llm_max_tokens"]
        )
        raw = resp.choices[0].message.content.strip()
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1:
            return json.loads(raw[s:e+1])
        return {}
    except Exception as e:
        print("LLM extract error:", e)
        return {}


# --------------------
# LLM Evaluation
# --------------------
def llm_evaluate(tender_json: dict):
    if LLM_CLIENT is None or not CONFIG["use_llm_eval"]:
        return {}
    try:
        prompt = EVAL_PROMPT.format(tender_json=json.dumps(tender_json))
        resp = LLM_CLIENT.chat.completions.create(model=CONFIG["llm_model"], messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=500)
        raw = resp.choices[0].message.content.strip()
        try:
            return json.loads(raw)
        except Exception:
            return {"pursue_recommendation": raw}
    except Exception as e:
        print("LLM eval error:", e)
        return {}

# --------------------
# Merge Regex & LLM Codes
# --------------------
def merge_candidates(regex_data: Dict[str, Any], llm_data: Dict[str, Any]) -> Dict[str, Any]:
    final = {}
    keys = set(list(regex_data.keys()) + list(llm_data.keys()))
    for k in keys:
        rv = regex_data.get(k)
        lv = llm_data.get(k)
        chosen = None
        if rv and isinstance(rv, str):
            # special sanitizers
            if k in ("emd", "tender_fee", "performance_guarantee"):
                rv = sanitize_amount_text(rv)
            elif k in ("submission_deadline", "publication_date", "bid_opening_date"):
                # keep date only
                sd = sanitize_date_like(rv)
                rv = sd or rv
            # validate
            if regex_value_valid(k, rv):
                chosen = rv
        if chosen is None and lv:
            # try LLM candidate
            if isinstance(lv, str):
                if k in ("emd", "tender_fee", "performance_guarantee"):
                    lv = sanitize_amount_text(lv)
                elif k in ("submission_deadline", "publication_date", "bid_opening_date"):
                    lv = sanitize_date_like(lv) or lv
                if regex_value_valid(k, lv):
                    chosen = lv
            else:
                chosen = lv
        if chosen is None:
            # defaults
            chosen = [] if k in ("contact_emails", "contact_phones", "projects") else ""
        final[k] = chosen

    # post-lists cleanup

    final["contact_emails"] = emails_cleanup(final.get("contact_emails") if isinstance(final.get("contact_emails"), list) else [])

    final["contact_phones"] = phones_cleanup(final.get("contact_phones") if isinstance(final.get("contact_phones"), list) else [])

    # category auto-detect if missing
    final["category"] = detect_category(final.get("title",""), final.get("scope_of_work",""), final.get("category",""))
    return final

def read_json_safe(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
    


# --------------------
# Chroma Vector Store DB
# --------------------
class ChromaVectorStore:
    def __init__(self, collection_name: str = "tenders"):
        # chromadb client (in-memory / local by default)
        self.client = chromadb.Client()
        # wrapper that uses sentence-transformers to embed text
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        # create or get collection (idempotent)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=self.embedding_fn
        )

    def add_documents(self, docs: List[Dict[str, Any]]):

        ids = [d["id"] for d in docs]
        documents = [d["text"] for d in docs]
        metadatas = []
        for d in docs:
            # convert metadata to simple dict of strings/numbers
            try:
                # use your existing clean_metadata() helper if available
                m = clean_metadata(d.get("meta", {}))
            except Exception:
                m = {}
            metadatas.append(m)

        # Add to collection (chromadb handles duplicates if same id used)
        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, query: str, k: int = 5):
        try:
            results = self.collection.query(query_texts=[query], n_results=k)
        except Exception as e:
            # return empty on error but log to console
            print("Chroma query error:", e)
            return []

        hits = []
        # results keys are e.g. "ids", "distances", "metadatas"
        if not results or "ids" not in results or len(results["ids"]) == 0:
            return hits

        for i in range(len(results["ids"][0])):
            hits.append({
                "meta": results["metadatas"][0][i],
                "score": results["distances"][0][i]
            })
        return hits


# --------------------
# UI helpers (kept)
# --------------------
def summarize_to_bullets(text: str, max_bullets: int = 4) -> List[str]:
    if not text:
        return []
    s = str(text).strip()
    s = re.sub(r"\s+", " ", s)
    sentences = re.split(r'(?<=[\.\?\!])\s+', s)
    good = [sent.strip() for sent in sentences if len(sent.strip()) >= 25]
    if good:
        return good[:max_bullets]
    parts = [p.strip() for p in re.split(r'[,\n;]+', s) if len(p.strip()) >= 20]
    if parts:
        return parts[:max_bullets]
    n = max_bullets
    approx = max(30, len(s) // n)
    chunks = [s[i:i+approx].strip() for i in range(0, len(s), approx)]
    chunks = [c for c in chunks if c]
    return chunks[:max_bullets]


def confidence_gauge_figure(conf):
    pct = int(conf * 100) if conf is not None else 0
    fig = go.Figure(go.Indicator(mode="gauge+number", value=pct, number={'suffix': "%"},
                                 gauge={'axis': {'range': [0,100]}, 'bar': {'color': "#10B981"},
                                        'steps':[{'range':[0,45],'color':"#fee2e2"},{'range':[45,75],'color':"#fef9c3"},{'range':[75,100],'color':"#dcfce7"}]},
                                 title={'text':'Confidence'}))
    fig.update_layout(height=220, margin=dict(l=20,r=20,t=40,b=10))
    return fig

# --------------------
# Dash app (layout + callbacks) - MAIN (unchanged layout)
# --------------------
external_stylesheets = [dbc.themes.FLATLY, "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server
app.title = "TenderGPT (Dash)"

def navbar():
    logo_url = app.get_asset_url("Logo.png")
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.A(
                    dbc.Row([
                        dbc.Col(html.Img(src=logo_url, height="46px"), width="auto"),
                        dbc.Col(dbc.NavbarBrand("MeghaAI", className="ms-2"), style={"paddingLeft": "6px"})
                    ], align="center", className="g-0"),
                    href="/"
                ), width="auto"),
                dbc.Col(html.Div(), width="auto"),
                dbc.Col(dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Upload", href="/", id="nav-upload")),
                    dbc.NavItem(dbc.NavLink("Dashboard", href="/dashboard", id="nav-dashboard")),
                    dbc.NavItem(dbc.NavLink("Chat", href="/chat", id="nav-chat")),
                ], navbar=True), style={"textAlign":"right"}, width=True)
            ], align="center", className="w-100")
        ]),
        color="#550ea1", dark=True, sticky="top"
    )

def initial_detail_area():
    return dbc.Card(dbc.CardBody([html.P("Select a tender to view details.")]), className="h-100")

def upload_layout():
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Upload Tenders (PDF/DOCX/TXT)")),
                dbc.CardBody([
                    dcc.Upload(id="upload-files", children=html.Div(["Drag and drop or click to select files"]),
                               style={"width":"100%","height":"120px","lineHeight":"120px","borderWidth":"1px","borderStyle":"dashed","borderRadius":"6px","textAlign":"center","margin-bottom":"10px"},
                               multiple=True),
                    html.Div(id="upload-output"),
                    html.Br(),
                    dbc.Button("Process Uploaded Files", id="process-btn", color="primary"),
                    html.Br(), html.Br(),
                    dbc.Progress(id="process-progress", value=0, striped=True, animated=True, style={"height":"18px","display":"none"}),
                    html.Div(id="process-status", className="small text-muted mt-1")
                ])
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Upload Instructions")),
                dbc.CardBody([html.P("Upload PDF/DOCX/TXT tender documents. Extraction will run regex + optional LLM extraction."), html.P("LLM extraction/eval uses Azure OpenAI if configured.")])
            ])
        ], md=6)
    ])

def dashboard_layout():
    """Display dashboard tiles with tender summaries."""
    return html.Div([
        dbc.Row([dbc.Col(html.H3("Tender Dashboard"), md=8), dbc.Col(dbc.Button("Refresh KPIs", id="refresh-kpi", color="secondary"), md=4, style={"textAlign":"right"})]),
        html.Hr(),
        dbc.Row(id="kpi-row"),
        html.Hr(),
        dbc.Row([dbc.Col(html.Div(id="tender-tiles"), md=7), dbc.Col(html.Div(id="tender-detail-area", children=initial_detail_area()), md=5)])
    ])

def chat_layout():
    """Chat interface for querying processed tenders."""
    return html.Div([
        html.H3("TenderGPT Chat"),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.Div(id="chat-window", style={"maxHeight":"60vh","overflowY":"auto","padding":"10px","border":"1px solid #ddd","borderRadius":"8px"}),
                html.Br(),
                dbc.InputGroup([dbc.Input(id="chat-input", placeholder="Ask a question about tenders..."), dbc.Button("Send", id="chat-send", color="primary")])
            ], md=8),
            dbc.Col([html.H6("Context selector"), html.P("Choose a tender to include in context for the LLM:"), dcc.Dropdown(id="chat-context-select", multi=True, placeholder="Select tenders for context")], md=4)
        ])
    ])

app.layout = dbc.Container([
    dcc.Location(id="url", refresh=False),
    # html.Style(STYLE_CSS),
    navbar(),
    html.Br(),
    dcc.Store(id="tenders-store", data=[]),
    dcc.Store(id="chat-store", data=[]),
    dcc.Interval(id="progress-interval", interval=1*1000, n_intervals=0, disabled=True),
    html.Div(id="page-upload", children=upload_layout(), style={"display":"block"}),
    html.Div(id="page-dashboard", children=dashboard_layout(), style={"display":"none"}),
    html.Div(id="page-chat", children=chat_layout(), style={"display":"none"}),
], fluid=True)

@app.callback(Output("page-upload","style"), Output("page-dashboard","style"), Output("page-chat","style"), Input("url","pathname"))
def toggle_pages(pathname):
    if pathname is None or pathname == "/":
        return {"display":"block"}, {"display":"none"}, {"display":"none"}
    if pathname == "/dashboard":
        return {"display":"none"}, {"display":"block"}, {"display":"none"}
    if pathname == "/chat":
        return {"display":"none"}, {"display":"none"}, {"display":"block"}
    return {"display":"block"}, {"display":"none"}, {"display":"none"}

# --------------------
# Extraction worker
# --------------------

def _date_sanity_fix(final_obj: dict):
    """If bid_opening/submission year conflicts with publication year but day/month match, align to publication year."""
    pub = final_obj.get("publication_date","")
    if not pub or len(pub) != 10:  # expecting DD-MM-YYYY
        return
    try:
        pd, pm, py = int(pub[:2]), int(pub[3:5]), int(pub[6:10])
    except Exception:
        return
    for key in ("submission_deadline","bid_opening_date"):
        v = final_obj.get(key,"")
        if v and len(v) >= 10 and re.match(r"\d{2}-\d{2}-\d{4}", v):
            try:
                d, m, y = int(v[:2]), int(v[3:5]), int(v[6:10])
            except Exception:
                continue
            if d == pd and m == pm and y != py:
                final_obj[key] = f"{d:02d}-{m:02d}-{py}"
                log(f"Year adjusted for {key}: {v} -> {final_obj[key]}")


def pick_best_tender_id(cands: list[str]) -> str:
    if not cands : return ""
    def score(x: str) -> int:
        s = x.strip()
        sc = 0
        if "/" in s or "-" in s: sc += 3
        if re.search(r"\d", s): sc += 3
        if re.search(r"[A-Za-z]", s): sc += 2
        if 6 <= len(s) <= 40 : sc += 2
        return sc
    cands = [re.sub(r"^[#:;\-]+|[,:;\.\)]$", "", c).strip() for c in cands]
    cands = [c for c in cands if len(c) >= 5 and re.search(r"\d", c)]
    if not cands: return ""
    return sorted(cands, key=score, reverse=True)[0]

BANNED_DEADLINE_SNIPPETS = [
    "validity of bid", "validity period", "be informed later",
    "shall be intimated", "time shall be intimated", "of bid submission"
]

def looks_like_real_date(s: str) -> bool:
    return bool(re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", s)) or bool(re.search(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", s))


def deadline_window_ok(win: str) -> bool:
    w = win.lower()
    if any(b in w for b in BANNED_DEADLINE_SNIPPETS) and not looks_like_real_date(win):
        return False
    return True

def sanitize_date_like(x: str) -> str:
    if not x: return ""
    s = " ".join(x.split())
    # prefer DD-MM-YYYY
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b", s)
    if m:
        d, mth, y = map(int, (m.group(1), m.group(2), m.group(3)))
        if y < 100: y += 2000
        try:
            return f"{d:02d}-{mth:02d}-{y:04d}"
        except: pass
    # textual month
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b", s)
    if m:
        try:
            dt = datetime.strptime(" ".join(m.groups()), "%d %B %Y")
        except:
            dt = datetime.strptime(" ".join(m.groups()), "%d %b %Y")
        return dt.strftime("%d-%m-%Y")
    return ""



# ---------- PAGE / CHUNK HELPERS ----------
def split_into_pages(text: str) -> List[str]:
    pages = re.split(r"\n\s*Page\s*\d+\s*(?:of\s*\d+)?\s*\n", text, flags=re.I)
    # fallback: split every ~4000 chars at a newline boundary
    if len(pages) <= 1 and len(text) > 4500:
        lines = text.splitlines()
        pages, buf, cur = [], [], 0
        for ln in lines:
            buf.append(ln)
            cur += len(ln) + 1
            if cur > 4000:
                pages.append("\n".join(buf)); buf=[]; cur=0
        if buf: pages.append("\n".join(buf))
    return [p.strip() for p in pages if p and p.strip()]


def detect_global_header(text: str) -> Dict[str, str]:
    pages = split_into_pages(text)
    head = "\n\n".join(pages[:2]) if pages else text[:6000]
    out = {}
    m = re.search(r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)", head); 
    if m: out["title"] = m.group(1).strip()
    m = re.search(r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)", head)
    if m: out["issuing_authority"] = re.split(r"\n|,? *Address", m.group(1).strip())[0]
    m = re.search(r"(?i)\b(?:Bid\s*calling|Publication\s*Date|Date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", head)
    if m: out["publication_date"] = sanitize_date_like(m.group(1))
    # light location guess
    m = re.search(r"(?i)\b([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*,\s*India)\b", head)
    if m: out["location"] = m.group(1).strip()
    return out

def make_chunks_with_overlap(text: str, max_chars: int = 6000, overlap: int = 400) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+max_chars]
        # try to end at a paragraph boundary
        end = chunk.rfind("\n\n")
        if end != -1 and end > max_chars * 0.6:
            chunk = chunk[:end]
        chunks.append(chunk)
        i += max(1, len(chunk) - overlap)
    return chunks

# --- FAST ANCHOR WINDOWS (tiny slices around labels) ---

ANCHORS = {
    "submission_deadline": [r"(?i)bid\s*closing", r"(?i)last\s*date.*submission", r"(?i)submission\s*deadline"],
    "emd": [r"(?i)\bEMD\b", r"(?i)earnest\s*money"],
    "tender_fee": [r"(?i)(tender|bid|document)\s*fee"],
    "performance_guarantee": [r"(?i)performance\s*(guarantee|security)"],
    "contract_duration": [r"(?i)(period\s*of\s*completion|contract\s*duration|completion\s*period)"],
    "bid_opening_date": [r"(?i)bid\s*opening\s*date", r"(?i)opening\s*date"],
    "bid_opening_time": [r"(?i)opening\s*time"],
    "issuing_authority": [r"(?i)(issuing\s*authority|issued\s*by|organization|department|office)"],
    "title": [r"(?i)(name\s*of\s*work|title|project\s*title)"],
}


def _window_around_idx(lines, i, span=5):
    start = max(0, i - span)
    end = min(len(lines), i + span + 1)
    return "\n".join(lines[start:end]).strip()


def build_anchor_windows(full_text: str, max_windows_per_field: int = 2) -> dict:
    lines = full_text.splitlines()
    txt = full_text
    windows = {f: [] for f in ANCHORS.keys()}
    for field, pats in ANCHORS.items():
        hits = []
        for p in pats:
            for m in re.finditer(p, txt):
                # find line index of this match
                idx = txt[:m.start()].count("\n")
                hits.append(idx)
        # de-duplicate line indices, keep in-document order
        seen = set()
        uniq = []
        for h in hits:
            if h not in seen:
                uniq.append(h); seen.add(h)
        # collect windows
        for i in uniq[:max_windows_per_field]:
            win = _window_around_idx(lines, i, span=6)
            if len(win) > 1500:  # safety
                win = win[:1500]
            windows[field].append(win)
    return windows


def process_files_worker(encoded_items: List[Dict[str,str]]):
    prog_path = CONFIG["progress_file"]
    pending_path = CONFIG["pending_results_file"]
    total = len(encoded_items)
    progress = {"total": total, "done": 0, "status": "running", "current_file": ""}
    write_json(prog_path, progress)

    results = []
    for i, item in enumerate(encoded_items):
        fname = (item.get("filename","") or "")[:200]
        progress["current_file"] = fname
        write_json(prog_path, progress)
        log(f"Processing: {fname}")

        # decode
        try:
            header_b64 = item.get("content","")
            if "," in header_b64:
                _, b64 = header_b64.split(",",1)
            else:
                b64 = header_b64
            file_bytes = base64.b64decode(b64)
        except Exception:
            file_bytes = b""

        # save upload locally
        os.makedirs(CONFIG["uploads_dir"], exist_ok=True)
        upload_path = os.path.join(CONFIG["uploads_dir"], fname)
        try:
            with open(upload_path, "wb") as f:
                f.write(file_bytes)
        except Exception:
            pass

        # extract text
        text = extract_text(file_bytes, fname)
        # regex extract
        regexed = regex_extract(text)

        # LLM extract (hybrid)
        global_header = build_global_header(text)
        llm_extracted = {}
        if CONFIG["use_llm_extract"]:
            llm_raw = llm_extract_chunk(text, page_reference="all", global_header=global_header) or {}
            llm_extracted = postprocess_llm_json(lll := llm_raw)


        # merge with validation
        merged = merge_candidates(regexed, llm_extracted)

        # Build final object (schema-fixed)
        SCHEMA_KEYS = ["tender_id","category","title","location","issuing_authority","publication_date","submission_deadline",
                       "bid_opening_date","tender_value","bid_opening_time","emd","tender_fee","performance_guarantee","contract_duration",
                       "contact_emails","contact_phones","scope_of_work","eligibility_summary","required_documents",
                       "exclusion_criteria","disqualification_criteria","technical_documents","deliverables","projects",
                       "bidding_scope","short_summary"]
        final_obj = {}
        for k in SCHEMA_KEYS:
            val = merged.get(k, "")
            if k in ("contact_emails","contact_phones","projects"):
                if isinstance(val, list):
                    final_obj[k] = val
                elif isinstance(val, str) and val.strip():
                    final_obj[k] = [v.strip() for v in re.split(r"[,\n;]+", val) if v.strip()]
                else:
                    final_obj[k] = []
            else:
                final_obj[k] = val if val is not None else ""

        # Normalize dates to DD-MM-YYYY where possible
        def parse_date_to_ddmmYYYY_local(textval: str) -> str:
            if not textval:
                return ""
            s = str(textval).strip()
            patterns = [r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})']
            for pat in patterns:
                m = re.search(pat, s)
                if not m:
                    continue
                try:
                    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    if y < 100: y += 2000
                    return date(y, mo, d).strftime("%d-%m-%Y")
                except Exception:
                    continue
            return ""
        
        for dk in ("submission_deadline","publication_date","bid_opening_date"):
            raw = final_obj.get(dk,"")
            normalized = parse_date_to_ddmmYYYY_local(raw)
            if normalized:
                final_obj[dk] = normalized
        _date_sanity_fix(final_obj)


        if not final_obj.get("title"):
            m_now = re.search(r"(?is)Name\s*of\s*Work\s*[:\-]\s*(.+?)(?:\n|$)", text)
            if m_now:
                final_obj["title"] = m_now.group(1).strip()
                log(f"Title fallback (Name of Work): {final_obj['title']}")

        # Debug logs
        for key in ["tender_id","issuing_authority","emd","tender_fee","performance_guarantee","submission_deadline","bid_opening_date"]:
            log(f"{key}: {final_obj.get(key)}")

        eval_res = {}
        if CONFIG["use_llm_eval"]:
            eval_res = llm_evaluate(final_obj) or {}

        metadata = {"extraction_meta": {"regex_candidates": regexed, "llm_candidates": llm_extracted, "eval": eval_res}}

        safe_name = safe_stem(os.path.splitext(fname)[0])
        out_dir = os.path.join(CONFIG["extraction_output_dir"], safe_name)
        os.makedirs(out_dir, exist_ok=True)
        write_json(os.path.join(out_dir, "extraction.json"), final_obj)
        write_json(os.path.join(out_dir, "metadata.json"), metadata)

        tender_record = {
            "id": final_obj.get("tender_id") or fname,
            "title": final_obj.get("title") or fname,
            "location": final_obj.get("location") or "",
            "meta": final_obj,
            "eval": eval_res,
            "summary": final_obj.get("short_summary","") or final_obj.get("scope_of_work","") or "",
            "raw_text": text,
            "confidence": (eval_res.get("priority_score")/10.0) if eval_res.get("priority_score") else 0.7,
            "source_file": upload_path,
            "extraction_path": os.path.join(out_dir, "extraction.json")
        }
        results.append(tender_record)

        progress["done"] = i + 1
        write_json(prog_path, progress)
        time.sleep(0.05)

    progress["status"] = "done"
    progress["current_file"] = ""
    write_json(prog_path, progress)
    write_json(pending_path, {"results": results})

# --------------------
# Combined upload + poll callback (kept)
# --------------------
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
    State("tenders-store", "data"),
    prevent_initial_call=False
)
def combined_upload_and_poll(contents, filenames, process_clicks, n_intervals, tenders_data):
    tenders_data = tenders_data or []
    trig = ctx.triggered_id

    if trig == "upload-files":
        if not filenames:
            return html.Div("No files selected."), {"display":"none"}, 0, "", "", True, tenders_data
        preview = html.Div([
            html.Div("Files selected:", className="mb-2"),
            html.Ul([html.Li(name) for name in filenames]),
            html.Div("Click 'Process Uploaded Files' to extract and save.", className="text-muted small mt-2")
        ])
        return preview, {"display":"none"}, 0, "", "", True, tenders_data

    if trig == "process-btn":
        if not contents or not filenames:
            alert = dbc.Alert("No files to process. Please select files first.", color="warning")
            return alert, {"display":"none"}, 0, "", "", True, tenders_data

        encoded_items = [{"content": c, "filename": n} for c, n in zip(contents, filenames)]
        prog_initial = {"total": len(encoded_items), "done": 0, "status": "queued", "current_file": ""}
        write_json(CONFIG["progress_file"], prog_initial)
        thr = threading.Thread(target=process_files_worker, args=(encoded_items,), daemon=True)
        thr.start()
        preview = dbc.Alert([html.Div(f"Processing {len(encoded_items)} files in background:", style={"fontWeight":"600"}),
                             html.Ul([html.Li(n) for n in filenames])], color="info")
        style = {"display": "block"}
        value = 0
        children = f"0/{len(encoded_items)}"
        status = "Processing started..."
        return preview, style, value, children, status, False, tenders_data

    if trig == "progress-interval":
        prog = read_json_safe(CONFIG["progress_file"]) or {}
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
            pending = read_json_safe(CONFIG["pending_results_file"]) or {}
            results = pending.get("results", []) if pending else []
            existing = list(tenders_data)
            for r in results:
                sf = r.get("source_file")
                if not any((e.get("source_file") and e.get("source_file") == sf) for e in existing):
                    existing.append(r)
            try:
                os.remove(CONFIG["progress_file"])
            except Exception:
                pass
            try:
                os.remove(CONFIG["pending_results_file"])
            except Exception:
                pass
            return dash.no_update, {"display":"none"}, 100, f"{done}/{total}", "Processing complete.", True, existing

        if status == "error":
            return dash.no_update, {"display":"none"}, pct, children, "Error during processing. Check server logs.", True, tenders_data

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, True, tenders_data


# --------------------
# KPIs + tiles (unchanged except icon pick uses enhanced mapping)
# --------------------
@app.callback(Output("kpi-row","children"), Output("tender-tiles","children"),
              Input("tenders-store","data"), Input("refresh-kpi","n_clicks"),
              prevent_initial_call=False)
def render_dashboard(tenders_data, _):
    tenders_data = tenders_data or []

    # KPIs (unchanged)
    total_value = 0
    recommended = sum(1 for t in tenders_data if str(t.get("meta",{}).get("eval",{}).get("pursue_recommendation","")).upper() == "PURSUE")
    needs_review = sum(1 for t in tenders_data if not t.get("meta"))
    no_bid = sum(1 for t in tenders_data if str(t.get("meta",{}).get("eval",{}).get("pursue_recommendation","")).upper() == "DO NOT PURSUE")

    kpis = [
        dbc.Col(dbc.Card(dbc.CardBody([html.Div("Total Tender Value (EMD numeric sum)", className="text-muted small"), html.H4(f"₹ {total_value}") ])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.Div("Recommended to Bid", className="text-muted small"), html.H4(str(recommended), className="text-success")])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.Div("Needs Review", className="text-muted small"), html.H4(str(needs_review), className="text-warning")])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.Div("No-Bid", className="text-muted small"), html.H4(str(no_bid), className="text-danger")])), md=3),
    ]

    # --- Tiles: title + location + one-liner + deadline (+days) only ---
    tiles = []
    for idx, t in enumerate(tenders_data):
        title = t.get("title","Untitled")
        location = t.get("location","")
        meta = t.get("meta", {}) or {}

        # one-liner (with safe fallback)
        one_liner = (t.get("summary") or meta.get("short_summary") or meta.get("scope_of_work") or "").strip()
        one_liner = one_liner.split("\n")[0] if one_liner else ""
        if not one_liner:
            # clean fallback built from known fields (kept short)
            bits = []
            if meta.get("category"): bits.append(meta["category"])
            if meta.get("contract_duration"): bits.append(f"Duration: {meta['contract_duration']}")
            if meta.get("tender_value"): bits.append(f"Value: {meta['tender_value']}")
            if meta.get("emd"): bits.append(f"EMD: {meta['emd']}")
            if meta.get("tender_fee"): bits.append(f"Fee: {meta['tender_fee']}")
            one_liner = " • ".join(bits) or "—"
        one_liner = one_liner[:220]

        # deadline + days-left (strict validation; else N/A)
        raw_deadline = (meta.get("submission_deadline") or "").strip()
        deadline_display, days_left_text = ("N/A", "")
        parsed = None
        # Accept only clean date formats; anything else → N/A
        for fmt in ("%d-%m-%Y","%d/%m/%Y","%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw_deadline, fmt).date()
                break
            except:
                continue
        if parsed:
            deadline_display = parsed.strftime("%b %d, %Y")
            d = (parsed - date.today()).days
            days_left_text = f" • {d} days left" if d > 0 else (" • Due today" if d == 0 else f" • Closed {abs(d)} days ago")

        icon = pick_icon(meta.get("category",""), title, one_liner)

        tile = dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.Div(icon, className="tile-icon"),
                    html.Div([
                        html.H5(title, className="mb-1"),
                        html.Div(location, className="text-muted small mb-1"),
                        html.Div(one_liner, className="text-body-secondary"),
                        # ✅ Tender meta details
html.Div([
    html.Small("Tender ID", className="text-muted"),
    html.Div(meta.get("tender_id", "N/A"), className="fw-bold")
]),
html.Div([
    html.Small("Tender Date", className="text-muted"),
    html.Div(meta.get("publication_date", "N/A"))
]),
html.Div([
    html.Small("Tender Value", className="text-muted"),
    html.Div(meta.get("tender_value", "N/A"), className="text-success fw-bold")
]),

                        html.Div([
                            html.I(className="bi bi-clock me-1"),
                            html.Span("Submission: "),
                            html.Span(deadline_display),
                            html.Span(days_left_text, className="text-muted")
                        ], className="text-muted small mt-2")
                    ], className="w-100")
                ], className="d-flex gap-2 align-items-start"),
                html.Div(className="mt-2"),
                dbc.Row([
                    dbc.Col(dbc.Button("More Details", id={"type":"detail-btn","index":idx}, color="primary", size="sm"), width="auto"),
                    dbc.Col(dbc.Button("Ask AI", id={"type":"ask-btn","index":idx}, color="secondary", size="sm"), width="auto"),
                ], align="center", className="g-2")
            ]),
            className="mb-3 shadow-sm"
        )
        tiles.append(tile)

    return dbc.Row(kpis), tiles



# --------------------
# Unified detail / ask / chat (unchanged logic)
# --------------------
@app.callback(Output("tender-detail-area","children"), Output("chat-store","data"),
              Input({"type":"detail-btn","index":ALL},"n_clicks"),
              Input({"type":"ask-btn","index":ALL},"n_clicks"),
              Input("chat-send","n_clicks"),
              State("chat-input","value"),
              State("tenders-store","data"),
              State("chat-store","data"),
              State("chat-context-select","value"),
              prevent_initial_call=True)
def unified_tile_and_chat(detail_clicks, ask_clicks, chat_send_click, chat_input, tenders_data, chat_data, selected_context):
    triggered = ctx.triggered_id
    tenders_data = tenders_data or []
    chat_data = chat_data or []

    if isinstance(triggered, dict) and triggered.get("type") == "detail-btn":
        idx = triggered["index"]
        if idx < 0 or idx >= len(tenders_data):
            return dbc.Alert("Invalid tender selected."), chat_data
        t = tenders_data[idx]
        m = t.get("meta", {}) or {}

        # Core fields
        title = t.get("title","")
        location = t.get("location","")
        icon_span = sector_icon(m.get("category",""), title, t.get("summary",""))

        # Chips (value-only, short)
        chips = []
        def add_chip(label, val):
            if val and str(val).strip() and str(val).strip().lower() != "n/a":
                chips.append(html.Span(f"{label}: {val}", className="badge bg-light text-dark me-2 mb-2"))
        add_chip("EMD", m.get("emd",""))
        add_chip("Fee", m.get("tender_fee",""))
        add_chip("Duration", m.get("contract_duration",""))
        add_chip("Perf. Guarantee", m.get("performance_guarantee",""))
        add_chip("Deadline", m.get("submission_deadline",""))

        # Executive points (max 4, finance/time first)
        points = []
        for lbl in ["EMD","Tender Fee","Performance Guarantee","Contract Duration","Bid Opening Date","Bid Opening Time"]:
            key = lbl.lower().replace(" ","_")
            val = m.get(key, "")
            if val and str(val).strip() and str(val).strip().lower() != "n/a":
                points.append(f"{lbl}: {val}")

        # fallbacks if < 4 points
        if len(points) < 4:
            if m.get("issuing_authority"):
                points.append(f"Issuing Authority: {m.get('issuing_authority')}")
            if m.get("category"):
                points.append(f"Category: {m.get('category')}")
            # keep it max 4
        points = points[:4]

        # Confidence gauge
        conf = t.get("confidence", 0.7)

        detail_card = dbc.Card([
            dbc.CardHeader(
                html.Div([
                    html.Span(icon_span, className="me-2"),
                    html.H4(title, className="d-inline mb-0")
                ])
            ),
            dbc.CardBody([
                # Location
                html.Div([html.I(className="bi bi-geo-alt-fill me-1"), location or "—"], className="text-muted mb-2"),

                # Top row: Gauge + Chips
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=confidence_gauge_figure(conf), config={'displayModeBar':False},
                                    style={"width":"100%","height":"220px"}), md=4, xs=12),
                    dbc.Col(html.Div(chips, className="chips-vertical"), md=8, xs=12),
                ], className="align-items-start g-3"),

                html.Hr(className="my-3"),

                # Executive points
                html.H5("Executive Summary", className="mb-2"),
                html.Ul([html.Li(p) for p in points] if points else [html.Li("No key points available.")],
                        className="exec-points mb-0"),

                html.Hr(className="my-3"),

                # Contacts (small)
                html.H6("Contacts", className="mb-2"),
                html.Div([
                    html.Div(", ".join(m.get("contact_emails") or []) or "—", className="text-body"),
                    html.Div(", ".join(m.get("contact_phones") or []) or "—", className="text-body")
                ], className="small text-muted"),

                html.Div(className="mt-3"),
                html.Div([dbc.Button("Mark Bid", color="dark", className="me-2"), dbc.Button("Mark No-Bid", color="secondary")])
            ])
        ])
        return detail_card, chat_data

    if isinstance(triggered, dict) and triggered.get("type") == "ask-btn":
        idx = triggered["index"]
        if idx < 0 or idx >= len(tenders_data):
            return dash.no_update, chat_data
        t = tenders_data[idx]
        q = f"Brief me on tender '{t.get('title')}' in {t.get('location')}"
        chat_data = chat_data + [{"role":"user","content": q}]
        assistant_text = ""
        if LLM_CLIENT is not None:
            try:
                system_prompt = "You are TenderGPT, answer concisely using the tender context if provided."
                messages = [{"role":"system","content":system_prompt}, {"role":"user","content": q}]
                resp = LLM_CLIENT.chat.completions.create(model=CONFIG["llm_model"], messages=messages, temperature=0.2, max_tokens=300)
                assistant_text = resp.choices[0].message.content.strip()
            except Exception as e:
                assistant_text = f"LLM error: {e}"
        else:
            assistant_text = f"Simulated AI: Key points about '{t.get('title')}'."
        chat_data = chat_data + [{"role":"assistant","content": assistant_text}]
        return dash.no_update, chat_data

    if triggered == "chat-send":
        if not chat_input or str(chat_input).strip() == "":
            return dash.no_update, chat_data
        chat_data = chat_data + [{"role":"user","content": chat_input}]
        context_texts = []
        if selected_context and tenders_data:
            for sel in selected_context:
                try:
                    idx = int(sel)
                    if 0 <= idx < len(tenders_data):
                        context_texts.append(json.dumps(tenders_data[idx].get("meta",{})))
                except Exception:
                    continue
        assistant_text = ""
        if LLM_CLIENT is not None:
            try:
                system_prompt = "You are TenderGPT, answer concisely using the tender context if provided."
                messages = [{"role":"system","content": system_prompt}]
                if context_texts:
                    messages.append({"role":"system","content":"Tender context:\n" + "\n\n".join(context_texts)})
                messages.append({"role":"user","content": chat_input})
                resp = LLM_CLIENT.chat.completions.create(model=CONFIG["llm_model"], messages=messages, temperature=0.2, max_tokens=300)
                assistant_text = resp.choices[0].message.content.strip()
            except Exception as e:
                assistant_text = f"LLM error: {e}"
        else:
            assistant_text = "Simulated AI response: LLM client not configured."
        chat_data = chat_data + [{"role":"assistant","content": assistant_text}]
        return dash.no_update, chat_data

    return dash.no_update, chat_data


@app.callback(Output("chat-window","children"), Input("chat-store","data"))
def render_chat_window(chat_data):
    chat_data = chat_data or []
    children = []
    for m in chat_data:
        if m["role"] == "user":
            children.append(html.Div([html.Div("You", style={"fontSize":"12px","color":"#444"}), html.Div(m["content"], style={"background":"#e8e4f7","padding":"8px","borderRadius":"8px","textAlign":"right"})], style={"margin":"8px 0","textAlign":"right"}))
        else:
            children.append(html.Div([html.Div("TenderGPT", style={"fontSize":"12px","color":"#444"}), html.Div(m["content"], style={"background":"#fff","padding":"8px","borderRadius":"8px","border":"1px solid #ddd"})], style={"margin":"8px 0","textAlign":"left"}))
    return children


@app.callback(Output("chat-context-select","options"), Input("tenders-store","data"))
def populate_chat_context(tenders_data):
    tenders_data = tenders_data or []
    return [{"label": t.get("title", f"Tender {i+1}"), "value": str(i)} for i, t in enumerate(tenders_data)]

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8050
    url = f"http://{host}:{port}"
    webbrowser.open_new_tab(url)
    app.run(host=host, port=port, debug=True)

