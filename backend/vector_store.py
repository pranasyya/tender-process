import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import json
import os

# --------------------
# Helper
# --------------------
def clean_metadata(meta: dict) -> dict:
    """
    Sanitize and normalize tender metadata values for JSON serialization and display.
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

# --------------------
# Chroma Vector Store DB
# --------------------
class ChromaVectorStore:
    def __init__(self, collection_name: str = "tenders"):
        self.client = chromadb.Client()
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=self.embedding_fn
        )

    def add_documents(self, docs: List[Dict[str, Any]]):
        ids = [d["id"] for d in docs]
        documents = [d["text"] for d in docs]
        metadatas = []
        for d in docs:
            try:
                m = clean_metadata(d.get("meta", {}))
            except Exception:
                m = {}
            metadatas.append(m)

        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, query: str, k: int = 5, where: dict = None):
        try:
            if where:
                results = self.collection.query(query_texts=[query], n_results=k, where=where)
            else:
                results = self.collection.query(query_texts=[query], n_results=k)
        except Exception as e:
            print("Chroma query error:", e)
            return []

        hits = []
        if not results or "ids" not in results or len(results["ids"]) == 0:
            return hits

        for i in range(len(results["ids"][0])):
            hits.append({
                "meta": results["metadatas"][0][i],
                "text": results["documents"][0][i] if "documents" in results else "",
                "score": results["distances"][0][i] if "distances" in results else 0
            })
        return hits
    
    def get_all(self):
         # Helper to retrieve all docs for dashboard
         try:
             # Chroma .get() returns all by default if no ids specified
             return self.collection.get()
         except Exception as e:
             print("Chroma get_all error:", e)
             return {}
