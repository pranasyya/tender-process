import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from core.utils import clean_metadata

class ChromaVectorStore:
    """ChromaDB vector store for tender documents"""
    
    def __init__(self, collection_name: str = "tenders"):
        self.client = chromadb.Client()
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
    
    def add_documents(self, docs: List[Dict[str, Any]]):
        """Add documents to vector store"""
        ids = [d["id"] for d in docs]
        documents = [d["text"] for d in docs]
        metadatas = [clean_metadata(d.get("meta", {})) for d in docs]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
        except Exception as e:
            print(f"Chroma query error: {e}")
            return []
        
        hits = []
        if results and "ids" in results and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                hits.append({
                    "meta": results["metadatas"][0][i],
                    "score": results["distances"][0][i]
                })
        
        return hits