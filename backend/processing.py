import os
import json
import base64
import time
import threading
from typing import List, Dict, Any
from datetime import date
import re

from config import CONFIG
from extraction import (
    extract_text, 
    regex_extract, 
    build_global_header, 
    llm_extract_chunk, 
    postprocess_llm_json, 
    merge_candidates,
    llm_evaluate,
    safe_stem
)
from vector_store import ChromaVectorStore, clean_metadata

# --------------------
# Utilities
# --------------------
def write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def log(msg: str):
    if CONFIG.get("debug_logs"):
        print(f"[Processing] {msg}")

def _date_sanity_fix(final_obj: dict):
    pub = final_obj.get("publication_date","")
    if not pub or len(pub) != 10:
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

# --------------------
# Worker
# --------------------
def process_files_worker(encoded_items: List[Dict[str,str]]):
    prog_path = CONFIG["progress_file"]
    total = len(encoded_items)
    progress = {"total": total, "done": 0, "status": "running", "current_file": ""}
    write_json(prog_path, progress)

    # Initialize Vector Store
    vector_store = ChromaVectorStore()
    
    docs_to_add = []

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
            log(f"Failed to decode {fname}")

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

        # LLM extract
        global_header = build_global_header(text)
        llm_extracted = {}
        if CONFIG["use_llm_extract"]:
            llm_raw = llm_extract_chunk(text, page_reference="all", global_header=global_header) or {}
            llm_extracted = postprocess_llm_json(llm_raw)

        # merge
        merged = merge_candidates(regexed, llm_extracted)

        # Build final object
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
        
        # Date normalization
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

        # LLM Eval
        eval_res = {}
        if CONFIG["use_llm_eval"]:
            eval_res = llm_evaluate(final_obj) or {}

        # Save artifacts
        metadata = {"extraction_meta": {"regex_candidates": regexed, "llm_candidates": llm_extracted, "eval": eval_res}}
        safe_name = safe_stem(os.path.splitext(fname)[0])
        out_dir = os.path.join(CONFIG["extraction_output_dir"], safe_name)
        os.makedirs(out_dir, exist_ok=True)
        write_json(os.path.join(out_dir, "extraction.json"), final_obj)
        write_json(os.path.join(out_dir, "metadata.json"), metadata)

        # Prepare for Vector Store
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
            # Extra fields for dashboard filtering
            "tender_value": final_obj.get("tender_value", ""),
            "submission_deadline": final_obj.get("submission_deadline", ""),
            "contract_duration": final_obj.get("contract_duration", ""),
            "category": final_obj.get("category", ""),
            "emd": final_obj.get("emd", ""),
        }
        
        doc_entry = {
            "id": tender_record["id"],
            "text": text, # Storing full text for context
            "meta": tender_record
        }
        docs_to_add.append(doc_entry)

        progress["done"] = i + 1
        write_json(prog_path, progress)

    # Add to Vector Store
    if docs_to_add:
        log(f"Adding {len(docs_to_add)} documents to ChromaDB...")
        vector_store.add_documents(docs_to_add)

    progress["status"] = "done"
    progress["current_file"] = ""
    write_json(prog_path, progress)
    log("Processing Complete.")

def start_processing(encoded_items: List[Dict[str,str]]):
    t = threading.Thread(target=process_files_worker, args=(encoded_items,))
    t.start()
