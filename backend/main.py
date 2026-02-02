from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import base64
import json
import os
from pydantic import BaseModel

from config import CONFIG
from processing import start_processing
from vector_store import ChromaVectorStore
from extraction import get_chat_response

app = FastAPI(title="Tender Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str

@app.post("/analyse")
async def analyse(files: List[UploadFile] = File(...)):
    encoded_items = []
    for file in files:
        content = await file.read()
        b64 = base64.b64encode(content).decode("utf-8")
        encoded_items.append({"filename": file.filename, "content": b64})
    
    start_processing(encoded_items)
    return {"message": "Processing started", "file_count": len(files)}

@app.get("/progress")
async def get_progress():
    path = CONFIG["progress_file"]
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {"status": "error", "message": "Could not read progress"}
    return {"status": "idle", "total": 0, "done": 0}

@app.get("/tenders")
async def get_tenders():
    # Retrieve all tenders for dashboard
    vs = ChromaVectorStore()
    try:
        data = vs.get_all()
        # data has 'ids', 'metadatas' ...
        tenders = []
        if data and "metadatas" in data:
            for m in data["metadatas"]:
                if m:
                    # m is a dict, we might want to include id
                    tenders.append(m)
        return tenders
    except Exception as e:
        print("Error getting tenders:", e)
        # Return empty list instead of 500 to avoid breaking UI on empty DB
        return []

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    vs = ChromaVectorStore()
    hits = vs.search(req.query, k=3)
    resp = get_chat_response(req.query, hits)
    return {"response": resp, "context": hits}
