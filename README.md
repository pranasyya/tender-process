# 📄 TenderGPT - Intelligent Tender Analysis System

An advanced AI-powered tender document processing and analysis platform that extracts, analyzes, and provides intelligent insights from tender documents using OCR, NLP, and Large Language Models.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14.0+-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🌟 Features

### Core Capabilities
- **📑 Multi-Format Document Processing**: Supports PDF, DOCX, DOC, and TXT files
- **🔍 Intelligent Text Extraction**: Advanced OCR for scanned documents using PyMuPDF and Tesseract
- **🤖 AI-Powered Analysis**: Dual extraction using Regex patterns and LLM (OpenAI/Azure)
- **💬 Interactive Chat Interface**: Ask context-aware questions about uploaded tender documents
- **📊 Visual Dashboard**: Comprehensive tender analytics and filtering
- **🎯 Smart Evaluation**: Automated tender scoring and prioritization
- ** Real-time Progress Tracking**: Monitor document processing status

### Technical Features
- **Vector Search**: ChromaDB integration for semantic document search
- **Modern Frontend**: Next.js 14 with TypeScript, Tailwind CSS, and Radix UI
- **Fast Backend**: FastAPI-based Python backend with asynchronous processing
- **Configurable LLM Providers**: Support for both OpenAI and Azure OpenAI

## 🏗️ Architecture

```
tender-process/
├── backend/                 # Python FastAPI Backend
│   ├── main.py             # API Entry Point
│   ├── processing.py       # Core Processing Logic
│   ├── extraction.py       # OCR & LLM Extraction
│   ├── vector_store.py     # ChromaDB Integration
│   ├── config.py           # Configuration Management
│   ├── requirements.txt    # Python Dependencies
│   └── uploads/            # Temporary File Storage
│
└── frontend/                # Next.js Frontend
    ├── app/                # App Router Pages (Upload, Dashboard, Chat)
    ├── components/         # Reusable UI Components
    ├── lib/                # Utilities & API Client
    └── package.json        # Node Dependencies
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher
- **Review**: Ensure `AI Keys.xlsx` or `.env` is configured with valid API keys.

### Backend Setup

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   Ensure `AI Keys.xlsx` exists in the backend root or set environment variables for:
   - `OPENAI_API_KEY` or `AZURE_OPENAI_API_KEY`
   - `OPENAI_API_BASE` (if using Azure)

5. **Start the API Server**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### Frontend Setup

1. **Navigate to the frontend directory**
   ```bash
   cd frontend
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Start the Development Server**
   ```bash
   npm run dev
   ```
   The application will be available at `http://localhost:3000`.

## 📖 Usage

### 1. Upload Tender Documents
- Navigate to the **Upload** page (`/upload`).
- Drag and drop PDF or DOCX files.
- Click **Process Files**. The progress bar will show real-time analysis status.

### 2. View Dashboard
- Once processed, go to the **Dashboard** (`/dashboard`).
- View extracted details: Tender Value, EMD, Deadline, Location.
- Filter tenders by Value, Location, or Contract Type.
- Click "More Details" for a comprehensive view.

### 3. Ask AI (Chat)
- Click "Ask Megha" on a tender card or go to the **Chat** page (`/chat`).
- Select a tender context or ask general questions.
- Example: *"What is the submission deadline for the Ahmedabad project?"*

## 🔧 Configuration

### Backend Configuration
Modify `backend/config.py` to adjust:
- **LLM Settings**: Model name, temperature, max tokens.
- **OCR Settings**: Tesseract path.

### Frontend Configuration
Modify `frontend/lib/api.ts` to change the `API_BASE_URL` if deploying to a different environment.

## 📦 Key Dependencies

### Backend
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `pymupdf`: PDF text extraction
- `chromadb`: Vector storage
- `openai`: LLM integration
- `pandas`: Data handling

### Frontend
- `next`: React Framework
- `axios`: API requests
- `lucide-react`: Icons
- `tailwindcss`: Styling

## 🧪 Troubleshooting

- **ModuleNotFoundError: No module named 'frontend'**: Ensure you do not have the `fitz` package installed. Uninstall it and install `pymupdf`.
- **Form data requires "python-multipart"**: Install it via `pip install python-multipart`.