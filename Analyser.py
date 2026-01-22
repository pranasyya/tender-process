def analyse_tender(file_path: str) -> dict:
    """
    Core tender extraction logic (NO UI code here)
    """
    import re
    import os
    import pdfplumber
    import fitz
    from datetime import datetime

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





    return {}

