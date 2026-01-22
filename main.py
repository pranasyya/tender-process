from fastapi import FastAPI, UploadFile, File
from analyser import analyse_tender
from models import TenderResponse
import shutil, os

app = FastAPI(title="Tender Analysis API")

@app.post("/analyse", response_model=TenderResponse)
async def analyse(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return analyse_tender(file_path)
