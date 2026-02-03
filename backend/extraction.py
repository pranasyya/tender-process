import re
import json
import os
import io
import base64
import tempfile
import fitz  # PyMuPDF
import docx2txt
import pytesseract
from PIL import Image
from typing import Any, Dict, List, Tuple
from datetime import datetime
from config import CONFIG

# Import OpenAI/Azure Client
try:
    from openai import OpenAI, AzureOpenAI
except Exception:
    OpenAI = None
    AzureOpenAI = None

# --------------------
# Build LLM Client
# --------------------
def build_client():
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
# Constants & Patterns
# --------------------
CLEAN_LINE_PATTERNS = [
    re.compile(r"^\s*\d+\s*\|\s*P\s*a\s*g\s*e.*$", re.I),  
]

BANNED_SNIPPETS = [
    "msme", "mse procurement", "public procurement", "make in india", "gem", "physical form",
    "drawn in favour", "bank", "ifsc", "dd/", "bg", "cheque", "demand draft",
    "annexure", "refundable", "to be notified later", "of receiving queries",
    "form of dd", "form of bg", "submitted along with", "covering letter"
]

REGEX_PATTERNS = {
    "tender_id": r"(?im)\b(?:Tender\s*(?:Ref\.?|No\.?)|NIT\s*No\.?|e-?Tender\s*(?:No\.|ID)|RFQ\s*No\.?|Tender\s*Document\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{4,})",
    "title": r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)",
    "issuing_authority": r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)",
    "location": r"(?i)\b(?:Location|Place\s*of\s*Bid|Place\s*of\s*Work)\s*[:\-]\s*(.+)",
    "publication_date": r"(?i)\b(?:Bid\s*calling|Publication\s*Date|Date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "submission_deadline": r"(?i)(?:Last\s*Date\s*(?:of)?\s*(?:Submission|Bid\s*Submission|Receipt)|Bid\s*Closing)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "bid_opening_date": r"(?i)\b(?:Bid\s*opening|Opening\s*Date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
    "bid_opening_time": r"(?i)\b(?:Opening\s*Time|Time)\s*[:\-]?\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:AM|PM)?)",
    "emd": r"(?i)\b(?:EMD(?:\s*Amount)?|Earnest\s*Money(?:\s*Deposit)?)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",
    "tender_fee": r"(?i)\b(?:Bid\s*Document\s*Fee|Tender\s*Fee|Document\s*Fee)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",
    "performance_guarantee": r"(?i)\b(?:Performance\s*(?:Security|Guarantee))\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,60})",
    "contract_duration": r"(?i)\b(?:Contract\s*Duration|Period\s*of\s*Completion|Duration)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,60})",
    "contact_emails": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "contact_phones": r"(?:(?:\+91[-\s]?)?[\(]?\d{3,5}[\)]?[-\s]?\d{5,8}|\b\d{10}\b)",
    "tender_value": r"(?i)\b(?:Estimated\s*Cost|Tender\s*Value|Project\s*Cost|Approx\.?\s*Value)\b[^\n\r]{0,30}?[:\-]?\s*([^\n\r]{1,120})",
}

LIST_FIELDS = {"contact_emails", "contact_phones", "projects"}

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
  "tender_value": "",
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

EXTRACTION GUIDELINES:
- If a field is not present, use "N/A" for strings and [] for arrays, BUT use your best judgement to infer from context.
- Dates: Preferred "DD-MM-YYYY". If approximate, provide as found.
- Times: Preferred "HH:MM AM/PM".
- Monetary fields: concise values like "₹ 70,000", "Rs. 1 Lakh", "2%".
- Issuing Authority: Organization name.
- Category: Choose best-fit from: {categories}
- Scope of Work: concise description (approx 400 chars).
- Short Summary: A COMPREHENSIVE summary (approx 100-150 words) covering scope, key dates, and requirements. GENERATE THIS from the content; do NOT return "N/A".
- Projects: list distinct sub-projects if any.

CRITICAL EXTRACTION RULES:
- tender_id: ONLY extract if it appears verbatim in TEXT (e.g., "Tender ID", "NIT No", "Ref No"). Do NOT infer or generate.
- publication_date: Look for the earliest date mentioned as issue/start date.

OUTPUT FORMAT:
- Return JSON only. No markdown, no commentary, no trailing text.
"""

LLM_FIELD_PROMPT_TEMPLATE = r"""
You are an information extraction system. Extract ONLY the fields in SCHEMA from the TEXT.
Use GLOBAL_HEADER as context if the header appears only once in the document.

SCHEMA = {schema_json}

GLOBAL_HEADER (if provided):
{global_header}

TEXT (Page/Chunk = {page_reference}):
{chunk_text}

EXTRACTION GUIDELINES:
- If a field is not present, use "N/A" for strings and [] for arrays, BUT use your best judgement to infer from context.
- Dates: Preferred "DD-MM-YYYY". If approximate, provide as found.
- Times: Preferred "HH:MM AM/PM".
- Monetary fields: concise values like "₹ 70,000", "Rs. 1 Lakh", "2%".
- Issuing Authority: Organization name.
- Category: Choose best-fit from: {categories}
- Scope of Work: concise description (approx 400 chars).
- Short Summary: A COMPREHENSIVE summary (approx 100-150 words) covering scope, key dates, and requirements. GENERATE THIS from the content; do NOT return "N/A".
- tender_id: ONLY extract if it appears verbatim in TEXT. Do NOT infer or generate.

OUTPUT FORMAT:
- Return JSON only. No markdown, no commentary, no trailing text.
"""

EVAL_PROMPT = """
You are a business analyst. Based on the tender details below, return a JSON object with:
- priority_score (1-10, number)
- recommendation (PURSUE / REVIEW / DO NOT PURSUE)
- key_risks (short string summarizing key risks or gaps)

Return JSON only.

Tender JSON:
{tender_json}
"""

# --------------------
# Core Functions
# --------------------

def clean_text(text: str) -> str:
    if not text:
        return text
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
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = s.replace("mailto:", "").replace("Mailto:", "")
    s = s.replace("file://", "")
    return s

def extract_text(file_bytes: bytes, filename: str) -> str:
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
                    if CONFIG.get("tesseract_cmd"):
                         pytesseract.pytesseract.tesseract_cmd = CONFIG["tesseract_cmd"]
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
    return clean_text(text)

def regex_extract(text: str) -> Dict[str, Any]:
    extracted = {}
    head = text[:4000]

    # Header-based fields (more reliable for cover pages)
    tid = extract_tender_id_from_head(head)
    if tid:
        extracted["tender_id"] = tid
    title = extract_title_from_head(head)
    if title:
        extracted["title"] = title
    ia = extract_issuing_authority_from_head(head)
    if ia:
        extracted["issuing_authority"] = ia
    loc = extract_location_from_text(text)
    if loc:
        extracted["location"] = loc

    if "tender_id" not in extracted:
        tender_id_patterns = [
            r"Tender\s*(?:Ref\.?|ID|No\.?|Reference|Number)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"NIT\s*No\.?\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"e-?Tender\s*(?:No\.|ID|Reference)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"Bid\s*(?:No\.|ID|Reference)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"RFQ\s*No\.?\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        ]
        for pat in tender_id_patterns:
            m = re.search(pat, text, re.I | re.S)
            if m:
                tender_id_candidate = m.group(1).strip()
                if len(tender_id_candidate) >= 3 and tender_id_candidate.upper() != "N/A":
                    extracted["tender_id"] = tender_id_candidate
                    break
    if "tender_id" not in extracted:
        fallback = re.findall(r"\b[A-Z]{2,}-\d+\b", text)
        if fallback:
            extracted["tender_id"] = fallback[0]

    date_label_patterns = [
        r"(?:Publication\s*Date|Bid\s*Calling\s*Date|Date\s*of\s*Issue|Advertised\s*Date)\s*[:\-]?\s*([0-3]?\d[./-][0-1]?\d[./-]\d{2,4})",
        r"\b([0-3]?\d[./-][0-1]?\d[./-]\d{2,4})\b",
        r"\b([0-3]?\d\s*(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\s*\d{4})\b"
    ]
    for pat in date_label_patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            extracted["publication_date"] = m.group(1).strip()
            break

    for field, pattern in REGEX_PATTERNS.items():
        if field in extracted:
            continue
        if field in ["contact_emails", "contact_phones"]:
            matches = re.findall(pattern, text, flags=re.I)
            extracted[field] = list(dict.fromkeys(m.strip() for m in matches if m and m.strip()))
        else:
            m = re.search(pattern, text, flags=re.I | re.S)
            extracted[field] = m.group(1).strip() if m else ""

    # Keyword-near extraction for monetary fields if regex got only labels
    if not extracted.get("emd") or extracted.get("emd","").strip().lower() in {"emd", "(emd)"}:
        amt = extract_amount_near_keyword(text, r"\b(?:EMD|Earnest\s*Money(?:\s*Deposit)?)\b")
        if amt:
            extracted["emd"] = amt
    if not extracted.get("tender_fee"):
        fee = extract_amount_near_keyword(text, r"\b(?:Tender\s*Fee|Bid\s*Document\s*Fee|Document\s*Fee)\b")
        if fee:
            extracted["tender_fee"] = fee

    return extracted

def build_global_header(full_text: str) -> dict:
    head = full_text[:6000]
    out = {}
    m = re.search(r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)", head)
    if m: out["title"] = m.group(1).strip()
    m = re.search(r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)", head)
    if m: out["issuing_authority"] = re.split(r"\n|,? *Address", m.group(1).strip())[0]
    m = re.search(r"(?i)\b(?:Bid\s*calling|Publication\s*Date|Date\s*of\s*issue)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", head)
    if m: out["publication_date"] = sanitize_date_like(m.group(1))
    m = re.search(r"(?i)\b([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*,\s*India)\b", head)
    if m: out["location"] = m.group(1).strip()
    return out

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

def llm_evaluate(tender_json: dict):
    if LLM_CLIENT is None or not CONFIG["use_llm_eval"]:
        return {}
    try:
        prompt = EVAL_PROMPT.format(tender_json=json.dumps(tender_json))
        resp = LLM_CLIENT.chat.completions.create(model=CONFIG["llm_model"], messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=500)
        raw = resp.choices[0].message.content.strip()
        try:
            data = json.loads(raw)
            # Backward-compat: map old keys if present
            if "pursue_recommendation" in data and "recommendation" not in data:
                data["recommendation"] = data.get("pursue_recommendation")
            return data
        except Exception:
            return {"recommendation": raw}
    except Exception as e:
        print("LLM eval error:", e)
        return {}

def evaluate_fallback(tender_json: dict) -> dict:
    """
    Simple heuristic evaluation when LLM isn't available.
    """
    risks = []
    if not tender_json.get("submission_deadline") or tender_json.get("submission_deadline") == "N/A":
        risks.append("Submission deadline not found")
    if not tender_json.get("emd") or tender_json.get("emd") == "N/A":
        risks.append("EMD not specified")
    if not tender_json.get("scope_of_work") or tender_json.get("scope_of_work") == "N/A":
        risks.append("Scope of work not summarized")

    priority = 6
    if tender_json.get("emd") and tender_json.get("emd") != "N/A":
        priority = 7
    if tender_json.get("submission_deadline") and tender_json.get("submission_deadline") != "N/A":
        priority = max(priority, 7)

    return {
        "priority_score": priority,
        "recommendation": "REVIEW",
        "key_risks": "; ".join(risks) if risks else "No major risks detected from extracted fields"
    }

def postprocess_llm_json(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d or {})
    for k in ("publication_date","submission_deadline","bid_opening_date"):
        v = out.get(k, "")
        out[k] = sanitize_date_like(v) or ("N/A" if v else "N/A")
    t = out.get("bid_opening_time","").strip()
    mt = re.match(r"(?i)^\s*(\d{1,2})[:.](\d{2})\s*(AM|PM)?\s*$", t)
    out["bid_opening_time"] = (f"{int(mt.group(1)):02d}:{mt.group(2)} {mt.group(3) or 'PM'}".upper() if mt else ("N/A" if t else "N/A"))
    for k in ("emd","tender_fee","performance_guarantee","tender_value"):
        v = sanitize_amount_text(out.get(k,""))
        out[k] = v if (v and re.search(r"\d", v)) else "N/A"
    dur = out.get("contract_duration","").strip()
    if dur and len(dur) > 40:
        m = re.search(r"(?i)\b(\d+\s*(?:day|days|week|weeks|month|months|year|years))\b", dur)
        out["contract_duration"] = m.group(1) if m else "N/A"
    elif not dur:
        out["contract_duration"] = "N/A"
    ia = out.get("issuing_authority","").strip()
    if (not re.search(r"[A-Za-z]", ia)) or any(w in ia.lower() for w in ["msme","mse procurement","public procurement","make in india","gem"]):
        out["issuing_authority"] = "N/A"
    out["contact_emails"] = emails_cleanup(out.get("contact_emails") if isinstance(out.get("contact_emails"), list) else [])
    out["contact_phones"] = phones_cleanup(out.get("contact_phones") if isinstance(out.get("contact_phones"), list) else [])
    cats = set(ICON_STYLE_MAP.keys())
    if out.get("category") not in cats:
        out["category"] = ""
    for k, limit in (("scope_of_work", 1000), ("short_summary", 2000), ("eligibility_summary", 800), ("required_documents", 800)):
        v = (out.get(k) or "").strip()
        out[k] = v[:limit]
    return out

def merge_candidates(regex_data: Dict[str, Any], llm_data: Dict[str, Any]) -> Dict[str, Any]:
    final = {}
    keys = set(list(regex_data.keys()) + list(llm_data.keys()))
    for k in keys:
        rv = regex_data.get(k)
        lv = llm_data.get(k)
        if k in LIST_FIELDS:
            combined: List[str] = []
            for src in (rv, lv):
                if isinstance(src, list):
                    combined.extend([s for s in src if s])
                elif isinstance(src, str) and src.strip():
                    combined.extend([s.strip() for s in re.split(r"[,\n;]+", src) if s.strip()])
            final[k] = list(dict.fromkeys(combined))
            continue
        chosen = None
        if rv and isinstance(rv, str):
            if k in ("emd", "tender_fee", "performance_guarantee"):
                rv = sanitize_amount_text(rv)
            elif k in ("submission_deadline", "publication_date", "bid_opening_date"):
                sd = sanitize_date_like(rv)
                rv = sd or rv
            if regex_value_valid(k, rv):
                chosen = rv
        if chosen is None and lv:
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
            chosen = ""
        final[k] = chosen
    final["contact_emails"] = emails_cleanup(final.get("contact_emails") if isinstance(final.get("contact_emails"), list) else [])
    final["contact_phones"] = phones_cleanup(final.get("contact_phones") if isinstance(final.get("contact_phones"), list) else [])
    final["category"] = detect_category(final.get("title",""), final.get("scope_of_work",""), final.get("category",""))
    return final

# --------------------
# Helpers
# --------------------

def is_empty_value(field: str, value: Any) -> bool:
    if field in LIST_FIELDS:
        return not value or (isinstance(value, list) and len(value) == 0)
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().upper() in {"N/A", "NA", "NONE"}
    return False

def schema_for_fields(fields: List[str]) -> Dict[str, Any]:
    return {f: ([] if f in LIST_FIELDS else "") for f in fields}

def merge_llm_dicts(dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for d in dicts or []:
        for k, v in (d or {}).items():
            if k in LIST_FIELDS and isinstance(v, list):
                existing = merged.get(k, [])
                combined = []
                for item in (existing or []) + v:
                    if item and item not in combined:
                        combined.append(item)
                merged[k] = combined
                continue
            if is_empty_value(k, v):
                continue
            if is_empty_value(k, merged.get(k)):
                merged[k] = v
    return merged

def llm_extract_fields(chunk_text: str, fields: List[str], page_reference: str = "rag", categories: List[str] = None, global_header: dict = None) -> Dict[str, Any]:
    if LLM_CLIENT is None or not CONFIG["use_llm_extract"]:
        return {}
    if not chunk_text or not chunk_text.strip():
        return {}
    try:
        cats = categories or list(ICON_STYLE_MAP.keys())
        schema_json = json.dumps(schema_for_fields(fields), ensure_ascii=False)
        prompt = LLM_FIELD_PROMPT_TEMPLATE.format(
            chunk_text=chunk_text[:15000],
            categories=cats,
            page_reference=page_reference,
            global_header=json.dumps(global_header or {}, ensure_ascii=False),
            schema_json=schema_json
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

def chunk_text(text: str, max_chars: int = 3500, overlap: int = 400) -> List[str]:
    if not text:
        return []
    size = max(500, int(max_chars))
    overlap = max(0, min(int(overlap), size - 1))
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        chunk = text[start:end]
        if end < n:
            nl = chunk.rfind("\n")
            if nl != -1 and nl > size - 300:
                end = start + nl
                chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap)
        if start >= n:
            break
    return chunks

def build_context_from_hits(hits: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    if not hits:
        return ""
    parts: List[str] = []
    seen = set()
    total = 0
    for h in hits:
        t = (h.get("text") or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        if total + len(t) > max_chars:
            t = t[: max_chars - total]
        parts.append(t)
        total += len(t)
        if total >= max_chars:
            break
    return "\n\n".join(parts)

def extract_tender_id_from_head(head: str) -> str:
    if not head:
        return ""
    for line in head.splitlines()[:20]:
        s = line.strip()
        if not s or len(s) < 6:
            continue
        if re.fullmatch(r"[A-Z0-9][A-Z0-9/._-]{5,}", s) and any(ch.isdigit() for ch in s):
            return s
        m = re.search(r"(?i)\b(?:Tender|NIT|RFP|RFQ|Ref|Bid)\b[^A-Za-z0-9]*([A-Z0-9/._-]{4,})", s)
        if m:
            return m.group(1).strip()
    return ""

def extract_title_from_head(head: str) -> str:
    if not head:
        return ""
    lines = [l.strip() for l in head.splitlines() if l.strip()]
    for i, line in enumerate(lines[:20]):
        if re.search(r"Request\s*for\s*Proposal", line, re.I):
            collected = []
            for nxt in lines[i+1:i+6]:
                if re.search(r"^(Page|Contents)\b", nxt, re.I):
                    break
                if nxt.lower() in {"for", "to"}:
                    continue
                collected.append(nxt)
            title = " ".join(collected).strip()
            if len(title) >= 10:
                return title.strip().strip("\"'")
    m = re.search(r"(?is)Request\s*for\s*Proposal.*?for\s+(.+)", head)
    if m:
        title_line = re.split(r"\n|$", m.group(1).strip())[0]
        if len(title_line) >= 10:
            return title_line.strip().strip("\"'")
    m = re.search(r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)", head)
    if m:
        return m.group(1).strip()
    return ""

def extract_issuing_authority_from_head(head: str) -> str:
    if not head:
        return ""
    lines = [l.strip() for l in head.splitlines() if l.strip()]
    for line in lines[:15]:
        if re.search(r"(Bureau|Department|Ministry|Authority|Directorate|Council|Corporation|Board|Commission)", line, re.I):
            return line
    return ""

def extract_location_from_text(text: str) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        if re.search(r"\b\d{6}\b", line):
            clean = re.sub(r"\s+", " ", line).strip()
            if 8 <= len(clean) <= 120:
                return clean
    return ""

def extract_amount_near_keyword(text: str, keyword_pattern: str, window: int = 400) -> str:
    if not text:
        return ""
    m = re.search(keyword_pattern, text, re.I)
    if not m:
        return ""
    snippet = text[m.start(): m.start() + window]
    m_amt = re.search(r"(?i)(₹|â‚¹|rs\.?|rupees|inr)\s*([0-9][\d,\.]*)\s*(lacks?|lakhs?|lacs?|crores?)?", snippet)
    if m_amt:
        return sanitize_amount_text(m_amt.group(0))
    m_pct = re.search(r"(?i)\b(\d{1,3}(?:\.\d{1,2})?)\s*%(\b|$)", snippet)
    if m_pct:
        return f"{m_pct.group(1)}%"
    return ""

def build_fallback_summary(meta: Dict[str, Any]) -> str:
    parts: List[str] = []
    title = (meta.get("title") or "").strip()
    issuing = (meta.get("issuing_authority") or "").strip()
    location = (meta.get("location") or "").strip()
    pub = (meta.get("publication_date") or "").strip()
    sub = (meta.get("submission_deadline") or "").strip()
    open_dt = (meta.get("bid_opening_date") or "").strip()
    emd = (meta.get("emd") or "").strip()
    fee = (meta.get("tender_fee") or "").strip()
    perf = (meta.get("performance_guarantee") or "").strip()
    duration = (meta.get("contract_duration") or "").strip()
    scope = (meta.get("scope_of_work") or "").strip()
    eligibility = (meta.get("eligibility_summary") or "").strip()

    if title:
        parts.append(f"This tender is for {title}.")
    if issuing:
        parts.append(f"Issued by {issuing}.")
    if location and location.upper() != "N/A":
        parts.append(f"Location: {location}.")
    dates = []
    if pub and pub.upper() != "N/A":
        dates.append(f"publication date {pub}")
    if sub and sub.upper() != "N/A":
        dates.append(f"submission deadline {sub}")
    if open_dt and open_dt.upper() != "N/A":
        dates.append(f"bid opening date {open_dt}")
    if dates:
        parts.append("Key dates include " + ", ".join(dates) + ".")
    money_bits = []
    if emd and emd.upper() != "N/A":
        money_bits.append(f"EMD {emd}")
    if fee and fee.upper() != "N/A":
        money_bits.append(f"Tender fee {fee}")
    if perf and perf.upper() != "N/A":
        money_bits.append(f"Performance guarantee {perf}")
    if money_bits:
        parts.append("Financial terms: " + "; ".join(money_bits) + ".")
    if duration and duration.upper() != "N/A":
        parts.append(f"Contract duration: {duration}.")
    if scope:
        parts.append(f"Scope of work: {scope}")
    if eligibility:
        parts.append(f"Eligibility highlights: {eligibility}")

    summary = " ".join(p.strip() for p in parts if p and p.strip())
    return summary[:1200].strip()

def build_fallback_summary_from_text(text: str, meta: Dict[str, Any]) -> str:
    """
    Create a short summary from raw text when structured fields are sparse.
    """
    if not text:
        return build_fallback_summary(meta)
    # Prefer paragraphs with key terms
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    keywords = ["invites", "request for proposal", "scope of work", "eligibility", "submission", "deadline"]
    for p in paragraphs[:20]:
        low = p.lower()
        if any(k in low for k in keywords) and len(p) > 80:
            return p[:1200]
    # Fallback to first non-empty lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        return " ".join(lines[:6])[:1200]
    return build_fallback_summary(meta)

def sanitize_amount_text(val: str) -> str:
    if not val:
        return ""
    s = " ".join(val.strip().split())
    for b in BANNED_SNIPPETS:
        if b in s.lower():
            return ""
    m_pct = re.search(r"(?i)\b(\d{1,3}(?:\.\d{1,2})?)\s*%(\b|$)", s)
    if m_pct:
        return f"{m_pct.group(1)}%"
    m_amt = re.search(r"(?i)(₹|â‚¹|rs\.?|rupees|inr)\s*([0-9][\d,\.]*)\s*(lacks?|lakhs?|lacs?|crores?)?", s)
    if m_amt:
        cur = "₹" if ("₹" in m_amt.group(1) or "â‚¹" in m_amt.group(1)) else "Rs."
        num = m_amt.group(2)
        unit = m_amt.group(3) or ""
        unit = unit.capitalize() if unit else ""
        return f"{cur} {num}{(' ' + unit) if unit else ''}"
    if re.search(r"\d", s):
        s = re.split(r"[.;]", s)[0]
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
    if field == "tender_id":
        if not re.search(r"\d", s):
            return False
    if field in ("emd", "tender_fee", "performance_guarantee"):
        if not re.search(r"\d", s):
            return False
        for b in BANNED_SNIPPETS:
            if b in low:
                return False
    if field == "issuing_authority":
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
        e = re.sub(r"(Cell|Ph|Tel|Phone)\b.*$", "", e, flags=re.I).strip()
        m = re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", e)
        if m and e not in clean:
            clean.append(e)
    return clean

def phones_cleanup(phones: List[str]) -> List[str]:
    HELPLINE_PREFIXES = ("+91", "0", "022", "012", "1800", "1860")
    out = []
    for p in phones or []:
        digits = re.sub(r"\D", "", p)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if digits.startswith("0") and len(digits) in (11,12):
            digits = digits.lstrip("0")
        if digits.startswith(HELPLINE_PREFIXES):
            continue
        if 8 <= len(digits) <= 10:
            if digits not in out:
                out.append(digits)
    return out

def detect_category(title: str, scope: str, existing: str = "") -> str:
    if existing:
        return existing
    combined = f"{title or ''} {scope or ''}".lower()
    for kw, cat in KEYWORDS_TO_CATEGORY.items():
        if kw in combined:
            return cat
    return existing or ""

def sanitize_date_like(x: str) -> str:
    if not x: return ""
    s = " ".join(x.split())
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b", s)
    if m:
        d, mth, y = map(int, (m.group(1), m.group(2), m.group(3)))
        if y < 100: y += 2000
        try:
            return f"{d:02d}-{mth:02d}-{y:04d}"
        except: pass
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b", s)
    if m:
        try:
            dt = datetime.strptime(" ".join(m.groups()), "%d %B %Y")
        except:
             try:
                dt = datetime.strptime(" ".join(m.groups()), "%d %b %Y")
             except:
                return ""
        return dt.strftime("%d-%m-%Y")
    return ""

def safe_stem(s: str) -> str:
    return re.sub(r'[\\/:\"*?<>|]+', '_', s).strip()

def get_chat_response(query: str, context: List[Dict]) -> str:
    if LLM_CLIENT is None:
        # Lightweight fallback using regex on retrieved context
        combined = ""
        for item in context:
            combined += (item.get("text","") or "") + "\n"
        if not combined.strip():
            return "LLM Client not available and no document context found."
        extracted = regex_extract(combined)
        q = query.lower()
        if "tender id" in q or "tender no" in q or "ref" in q:
            return extracted.get("tender_id") or "Tender ID not found in the available context."
        if "location" in q or "place" in q or "address" in q:
            return extracted.get("location") or "Location not found in the available context."
        if "deadline" in q or "last date" in q or "submission" in q:
            return extracted.get("submission_deadline") or "Submission deadline not found in the available context."
        if "emd" in q or "earnest" in q:
            return extracted.get("emd") or "EMD not found in the available context."
        if "fee" in q:
            return extracted.get("tender_fee") or "Tender fee not found in the available context."
        if "opening" in q:
            return extracted.get("bid_opening_date") or "Bid opening date not found in the available context."
        if "summary" in q or "scope" in q:
            fallback = build_fallback_summary_from_text(combined, extracted)
            return fallback or "Summary not available from the current context."
        # default fallback
        fallback = build_fallback_summary_from_text(combined, extracted)
        return fallback or "No relevant answer found in the available context."
    
    # Build context string
    ctx_str = ""
    for item in context:
        ctx_str += f"--- Document: {item.get('meta',{}).get('title','Unknown')} ---\n"
        ctx_str += f"{item.get('text','')[:3000]}\n\n" # Truncate per doc to avoid huge context
    
    system_prompt = f"""You are a helpful assistant answering questions about tender documents.
Use the provided context to answer the user's question. if the answer is not in the context, say so.
Context:
{ctx_str}
"""
    try:
        resp = LLM_CLIENT.chat.completions.create(
            model=CONFIG["llm_model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("Chat error:", e)
        return "Sorry, I encountered an error while processing your request."
