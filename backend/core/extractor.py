import io
import re
import tempfile
from typing import Optional, Tuple
import pymupdf as fitz
from PIL import Image
import pytesseract
import docx2txt
from app.config import Config

class TextExtractor:
    """Extract text from various document formats"""
    
    # Clean patterns
    CLEAN_LINE_PATTERNS = [
        re.compile(r"^\s*\d+\s*\|\s*P\s*a\s*g\s*e.*$", re.I),
    ]
    
    @staticmethod
    def extract(file_bytes: bytes, filename: str) -> str:
        """Extract text from PDF, DOCX, or TXT"""
        name = filename.lower()
        text = ""
        
        if name.endswith(".pdf"):
            text = TextExtractor._extract_pdf(file_bytes)
        elif name.endswith((".docx", ".doc")):
            text = TextExtractor._extract_docx(file_bytes)
        else:
            text = file_bytes.decode(errors="ignore")
        
        return TextExtractor.clean_text(text)
    
    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """Extract text from PDF with OCR fallback"""
        text = ""
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                ptext = page.get_text("text").strip()
                if ptext and len(ptext) >= 15:
                    text += ptext + "\n"
                else:
                    # OCR fallback for scanned PDFs
                    text += TextExtractor._ocr_page(page) + "\n"
            doc.close()
        except Exception as e:
            print(f"PDF extraction failed: {e}")
        return text
    
    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        """Extract text from DOCX"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                return docx2txt.process(tmp.name) or ""
        except Exception as e:
            print(f"DOCX extraction failed: {e}")
            return ""
    
    @staticmethod
    def _ocr_page(page) -> str:
        """Perform OCR on a PDF page"""
        try:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            return pytesseract.image_to_string(image, lang="eng")
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean extracted text"""
        if not text:
            return text
        
        # Remove headers/footers
        lines = text.splitlines()
        kept = []
        for ln in lines:
            drop = False
            for pat in TextExtractor.CLEAN_LINE_PATTERNS:
                if pat.search(ln):
                    drop = True
                    break
            if not drop:
                kept.append(ln)
        
        s = "\n".join(kept)
        # De-hyphenate
        s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
        # Normalize spaces
        s = re.sub(r"[ \t]+", " ", s)
        # Clean prefixes
        s = s.replace("mailto:", "").replace("Mailto:", "").replace("file://", "")
        
        return s