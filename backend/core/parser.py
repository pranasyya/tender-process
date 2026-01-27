import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.config import Config
from core.utils import sanitize_date_like, sanitize_amount_text

class RegexParser:
    """Regex-based field extraction"""
    
    PATTERNS = {
        "tender_id": r"(?im)\b(?:Tender\s*(?:Ref\.?|No\.?)|NIT\s*No\.?|e-?Tender\s*(?:No\.|ID)|RFQ\s*No\.?|Tender\s*Document\s*No\.?)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{4,})",
        "title": r"(?i)(?:Name\s*of\s*Work|Title|Project\s*Title)\s*[:\-]\s*(.+)",
        "issuing_authority": r"(?i)\b(?:Issued\s*By|Issuing\s*Authority|Organization|Department|Office)\s*[:\-]\s*(.+)",
        # ... add all other patterns
    }
    
    BANNED_SNIPPETS = [
        "msme", "mse procurement", "public procurement", "make in india", "gem",
        "physical form", "drawn in favour", "bank", "ifsc", "dd/", "bg", "cheque",
    ]
    
    @classmethod
    def extract(cls, text: str) -> Dict[str, Any]:
        """Extract fields using regex"""
        extracted = {}
        
        # Extract tender ID
        tender_id = cls._extract_tender_id(text)
        if tender_id:
            extracted["tender_id"] = tender_id
        
        # Extract dates
        dates = cls._extract_dates(text)
        extracted.update(dates)
        
        # Extract other fields
        for field, pattern in cls.PATTERNS.items():
            if field not in extracted:
                if field in ["contact_emails", "contact_phones"]:
                    matches = re.findall(pattern, text, flags=re.I)
                    extracted[field] = list(dict.fromkeys(m.strip() 
                                    for m in matches if m and m.strip()))
                else:
                    m = re.search(pattern, text, flags=re.I | re.S)
                    extracted[field] = m.group(1).strip() if m else ""
        
        return extracted
    
    @staticmethod
    def _extract_tender_id(text: str) -> Optional[str]:
        """Priority extraction for tender ID"""
        patterns = [
            r"Tender\s*(?:Ref\.?|ID|No\.?|Reference|Number)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"NIT\s*No\.?\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
            r"e-?Tender\s*(?:No\.|ID|Reference)\s*[:\-]?\s*([A-Za-z0-9_\/\-\.\(\)]{3,})",
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.I | re.S)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) >= 3 and candidate.upper() != "N/A":
                    return candidate
        
        return None
    
    @staticmethod
    def _extract_dates(text: str) -> Dict[str, str]:
        """Extract date fields"""
        dates = {}
        
        patterns = {
            "publication_date": r"(?:Publication\s*Date|Bid\s*Calling\s*Date|Date\s*of\s*Issue)\s*[:\-]?\s*([0-3]?\d[./-][0-1]?\d[./-]\d{2,4})",
            "submission_deadline": r"(?:Last\s*Date\s*(?:of)?\s*(?:Submission|Bid\s*Submission)|Bid\s*Closing)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
            "bid_opening_date": r"\b(?:Bid\s*opening|Opening\s*Date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        }
        
        for field, pattern in patterns.items():
            m = re.search(pattern, text, re.I | re.S)
            dates[field] = m.group(1).strip() if m else ""
        
        return dates