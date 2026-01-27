import os
import json
import time
import threading
import base64
from typing import Dict, List, Any
from app.config import Config
from core.extractor import TextExtractor
from core.parser import RegexParser
from core.llm_client import LLMClient
from core.utils import (
    save_upload, safe_stem, build_global_header, 
    merge_results, postprocess_llm_json
)

class FileProcessor:
    """Background file processor"""
    
    def __init__(self):
        self.llm_client = LLMClient.get_client()
        self.config = Config
    
    def process_files(self, encoded_items: List[Dict[str, str]]):
        """Process multiple files in background"""
        total = len(encoded_items)
        
        # Initialize progress
        progress = {
            "total": total,
            "done": 0,
            "status": "running",
            "current_file": ""
        }
        self._update_progress(progress)
        
        results = []
        for i, item in enumerate(encoded_items):
            fname = item.get("filename", "")[:200]
            progress["current_file"] = fname
            self._update_progress(progress)
            
            # Process single file
            result = self._process_single_file(item)
            if result:
                results.append(result)
            
            # Update progress
            progress["done"] = i + 1
            self._update_progress(progress)
            time.sleep(0.05)
        
        # Mark as complete
        progress.update({"status": "done", "current_file": ""})
        self._update_progress(progress)
        
        # Save results
        self._save_results(results)
        return results
    
    def _process_single_file(self, item: Dict[str, str]) -> Dict[str, Any]:
        """Process a single file"""
        try:
            # Decode file
            file_bytes = self._decode_file(item)
            filename = item.get("filename", "")
            
            # Save upload
            upload_path = save_upload(file_bytes, filename)
            
            # Extract text
            text = TextExtractor.extract(file_bytes, filename)
            
            # Regex extraction
            regex_results = RegexParser.extract(text)
            
            # LLM extraction
            llm_results = {}
            if Config.USE_LLM_EXTRACT:
                global_header = build_global_header(text)
                llm_results = self._llm_extract(text, global_header)
                llm_results = postprocess_llm_json(llm_results)
            
            # Merge results
            merged = merge_results(regex_results, llm_results)
            
            # Build final object
            final_obj = self._build_final_object(merged, text, filename)
            
            # LLM evaluation
            eval_result = {}
            if Config.USE_LLM_EVAL:
                eval_result = self._llm_evaluate(final_obj)
            
            # Save outputs
            output_dir = self._save_outputs(filename, final_obj, {
                "regex_candidates": regex_results,
                "llm_candidates": llm_results,
                "eval": eval_result
            })
            
            # Create record
            record = {
                "id": final_obj.get("tender_id") or filename,
                "title": final_obj.get("title") or filename,
                "location": final_obj.get("location") or "",
                "meta": final_obj,
                "eval": eval_result,
                "summary": final_obj.get("short_summary", "") or final_obj.get("scope_of_work", ""),
                "raw_text": text,
                "confidence": (eval_result.get("priority_score", 0) / 10.0) if eval_result else 0.7,
                "source_file": upload_path,
                "extraction_path": os.path.join(output_dir, "extraction.json")
            }
            
            return record
            
        except Exception as e:
            print(f"Error processing file: {e}")
            return {}
    
    def _decode_file(self, item: Dict[str, str]) -> bytes:
        """Decode base64 file content"""
        header_b64 = item.get("content", "")
        if "," in header_b64:
            _, b64 = header_b64.split(",", 1)
        else:
            b64 = header_b64
        return base64.b64decode(b64)
    
    def _llm_extract(self, text: str, global_header: Dict[str, Any]) -> Dict[str, Any]:
        """Extract using LLM"""
        # Implementation similar to original llm_extract_chunk
        pass
    
    def _llm_evaluate(self, tender_json: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate tender using LLM"""
        # Implementation similar to original llm_evaluate
        pass
    
    def _build_final_object(self, merged: Dict[str, Any], text: str, filename: str) -> Dict[str, Any]:
        """Build final tender object"""
        # Implementation
        pass
    
    def _save_outputs(self, filename: str, final_obj: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Save extraction outputs"""
        safe_name = safe_stem(os.path.splitext(filename)[0])
        out_dir = os.path.join(Config.EXTRACTION_OUTPUT_DIR, safe_name)
        os.makedirs(out_dir, exist_ok=True)
        
        with open(os.path.join(out_dir, "extraction.json"), "w", encoding="utf-8") as f:
            json.dump(final_obj, f, indent=2, ensure_ascii=False)
        
        with open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return out_dir
    
    def _update_progress(self, progress: Dict[str, Any]):
        """Update progress file"""
        with open(Config.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)
    
    def _save_results(self, results: List[Dict[str, Any]]):
        """Save pending results"""
        with open(Config.PENDING_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"results": results}, f, indent=2)