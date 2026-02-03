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
    safe_stem,
    chunk_text,
    llm_extract_fields,
    merge_llm_dicts,
    build_context_from_hits,
    is_empty_value,
    build_fallback_summary,
    build_fallback_summary_from_text,
    evaluate_fallback
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
# RAG Settings
# --------------------
RAG_CORE_FIELDS = [
    "tender_id", "category", "title", "location", "issuing_authority",
    "publication_date", "submission_deadline", "bid_opening_date", "bid_opening_time",
    "emd", "tender_fee", "performance_guarantee", "contract_duration", "tender_value",
    "contact_emails", "contact_phones"
]

RAG_CONTENT_FIELDS = [
    "scope_of_work", "eligibility_summary", "required_documents",
    "exclusion_criteria", "disqualification_criteria",
    "technical_documents", "deliverables", "projects", "bidding_scope"
]

RAG_SUMMARY_FIELDS = ["short_summary"]

RAG_CORE_QUERIES = [
    "Tender ID NIT No Ref No RFP RFQ",
    "Title Name of Work Project Title",
    "Issued by Issuing Authority Organization Department",
    "Publication Date Date of Issue Bid Calling",
    "Last date of submission Bid submission deadline",
    "Bid opening date time Opening Time",
    "EMD Earnest Money Deposit",
    "Tender Fee Bid Document Fee",
    "Performance Security Performance Guarantee",
    "Contract Duration Period of Completion",
    "Estimated Cost Tender Value Project Cost",
    "Contact person email phone address location"
]

RAG_CONTENT_QUERIES = [
    "Scope of Work",
    "Eligibility Criteria",
    "Technical Bid Documents",
    "Required Documents",
    "Exclusion criteria disqualification blacklist",
    "Deliverables",
    "Projects portals modules",
    "Bidding scope",
    "Timeline and Payments"
]

RAG_SUMMARY_QUERIES = [
    "Scope of Work",
    "Timeline and Payments",
    "Eligibility Criteria",
    "Submission deadline",
    "EMD Tender Fee Performance Security",
    "Deliverables"
]

def _rag_context(store: ChromaVectorStore, queries: List[str], where: dict, k_per_query: int = 3, max_chars: int = 12000) -> str:
    hits: List[Dict[str, Any]] = []
    for q in queries:
        hits.extend(store.search(q, k=k_per_query, where=where))
    return build_context_from_hits(hits, max_chars=max_chars)

# --------------------
# Worker
# --------------------
def process_files_worker(encoded_items: List[Dict[str,str]]):
    prog_path = CONFIG["progress_file"]
    total = len(encoded_items)
    progress = {"total": total, "done": 0, "status": "running", "current_file": ""}
    write_json(prog_path, progress)

    # Initialize Vector Stores
    tender_store = ChromaVectorStore(collection_name="tenders")
    chunk_store = ChromaVectorStore(collection_name="tender_chunks")
    
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
        safe_name = safe_stem(os.path.splitext(fname)[0])

        # chunk & index for RAG
        chunks = chunk_text(
            text,
            max_chars=CONFIG.get("rag_chunk_chars", 3500),
            overlap=CONFIG.get("rag_chunk_overlap", 400)
        )
        if chunks:
            chunk_docs = []
            for idx, ch in enumerate(chunks):
                chunk_docs.append({
                    "id": f"{safe_name}::chunk::{idx}",
                    "text": ch,
                    "meta": {
                        "doc_id": safe_name,
                        "chunk_id": idx,
                        "source_file": upload_path,
                        "title": fname
                    }
                })
            chunk_store.add_documents(chunk_docs)
        
        # regex extract
        regexed = regex_extract(text)

        # LLM extract (RAG-first with fallback)
        global_header = build_global_header(text)
        llm_extracted = {}
        if CONFIG["use_llm_extract"]:
            where = {"doc_id": safe_name}
            core_ctx = _rag_context(
                chunk_store,
                RAG_CORE_QUERIES,
                where,
                k_per_query=CONFIG.get("rag_top_k", 3),
                max_chars=CONFIG.get("rag_context_chars", 12000)
            )
            content_ctx = _rag_context(
                chunk_store,
                RAG_CONTENT_QUERIES,
                where,
                k_per_query=CONFIG.get("rag_top_k", 3),
                max_chars=CONFIG.get("rag_context_chars", 12000)
            )
            summary_ctx = _rag_context(
                chunk_store,
                RAG_SUMMARY_QUERIES,
                where,
                k_per_query=CONFIG.get("rag_top_k", 4),
                max_chars=CONFIG.get("rag_context_chars", 12000)
            )
            llm_parts = []
            if core_ctx:
                llm_parts.append(llm_extract_fields(core_ctx, RAG_CORE_FIELDS, page_reference="rag-core", global_header=global_header))
            if content_ctx:
                llm_parts.append(llm_extract_fields(content_ctx, RAG_CONTENT_FIELDS, page_reference="rag-content", global_header=global_header))
            if CONFIG.get("use_llm_summary", True) and summary_ctx:
                llm_parts.append(llm_extract_fields(summary_ctx, RAG_SUMMARY_FIELDS, page_reference="rag-summary", global_header=global_header))
            if llm_parts:
                llm_extracted = merge_llm_dicts(llm_parts)
                llm_extracted = postprocess_llm_json(llm_extracted)
            else:
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
                if is_empty_value(k, final_obj[k]):
                    final_obj[k] = "N/A"
        
        # Date normalization
        for dk in ("submission_deadline","publication_date","bid_opening_date"):
            raw = final_obj.get(dk,"")
            normalized = parse_date_to_ddmmYYYY_local(raw)
            if normalized:
                final_obj[dk] = normalized
        _date_sanity_fix(final_obj)

        # Ensure tender_id is actually present in the document text
        tender_id_val = (final_obj.get("tender_id") or "").strip()
        if tender_id_val and tender_id_val.upper() not in {"N/A", "NA"}:
            if tender_id_val.lower() not in text.lower():
                final_obj["tender_id"] = "N/A"

        if not final_obj.get("title") or final_obj.get("title") == "N/A":
            m_now = re.search(r"(?is)Name\s*of\s*Work\s*[:\-]\s*(.+?)(?:\n|$)", text)
            if m_now:
                final_obj["title"] = m_now.group(1).strip()
        if not final_obj.get("title"):
            final_obj["title"] = "N/A"

        if not final_obj.get("category"):
            final_obj["category"] = "N/A"

        if not final_obj.get("short_summary") or final_obj.get("short_summary") == "N/A":
            fallback_summary = build_fallback_summary(final_obj)
            if not fallback_summary:
                fallback_summary = build_fallback_summary_from_text(text, final_obj)
            final_obj["short_summary"] = fallback_summary if fallback_summary else "Summary not available"

        # LLM Eval
        eval_res = {}
        if CONFIG["use_llm_eval"]:
            eval_res = llm_evaluate(final_obj) or {}
        if not eval_res:
            eval_res = evaluate_fallback(final_obj) or {}

        # Save artifacts
        metadata = {"extraction_meta": {"regex_candidates": regexed, "llm_candidates": llm_extracted, "eval": eval_res}}
        out_dir = os.path.join(CONFIG["extraction_output_dir"], safe_name)
        os.makedirs(out_dir, exist_ok=True)
        write_json(os.path.join(out_dir, "extraction.json"), final_obj)
        write_json(os.path.join(out_dir, "metadata.json"), metadata)

        # Prepare for Vector Store
        tender_record = {
            "id": safe_name or fname,
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
        tender_store.add_documents(docs_to_add)

    progress["status"] = "done"
    progress["current_file"] = ""
    write_json(prog_path, progress)
    log("Processing Complete.")

def start_processing(encoded_items: List[Dict[str,str]]):
    t = threading.Thread(target=process_files_worker, args=(encoded_items,))
    t.start()
