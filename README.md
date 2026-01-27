# 📄 TenderGPT - Intelligent Tender Analysis System

An advanced AI-powered tender document processing and analysis platform that extracts, analyzes, and provides intelligent insights from tender documents using OCR, NLP, and Large Language Models.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16.0+-black.svg)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🌟 Features

### Core Capabilities
- **📑 Multi-Format Document Processing**: Supports PDF, DOCX, DOC, and TXT files
- **🔍 Intelligent Text Extraction**: Advanced OCR for scanned documents with PyMuPDF and Tesseract
- **🤖 AI-Powered Analysis**: Dual extraction using Regex patterns and LLM (OpenAI/Azure)
- **💬 Interactive Chat Interface**: Ask questions about uploaded tender documents
- **📊 Visual Dashboard**: Comprehensive tender analytics and comparison
- **🎯 Smart Evaluation**: Automated tender scoring and prioritization
- **🔄 Batch Processing**: Upload and process multiple tender documents simultaneously
- **📈 Real-time Progress Tracking**: Monitor document processing status

### Technical Features
- **Vector Search**: ChromaDB integration for semantic document search
- **Responsive UI**: Modern Next.js frontend with Radix UI components
- **RESTful Backend**: Dash-based Python backend with modular architecture
- **Configurable LLM Providers**: Support for both OpenAI and Azure OpenAI

## 🏗️ Architecture

```
tender-process/
├── backend/                 # Python backend
│   ├── app/                # Dash application
│   │   ├── main.py        # Entry point
│   │   ├── config.py      # Configuration
│   │   ├── layouts.py     # UI layouts
│   │   └── callbacks.py   # Event handlers
│   ├── core/              # Core processing logic
│   │   ├── extractor.py   # Text extraction
│   │   ├── parser.py      # Regex parsing
│   │   ├── processor.py   # File processing
│   │   ├── llm_client.py  # LLM integration
│   │   ├── vector_store.py # Vector database
│   │   └── utils.py       # Utilities
│   ├── requirements.txt   # Python dependencies
│   ├── setup.py          # Setup script
│   └── run.py            # Main runner
└── frontend/             # Next.js frontend
    ├── app/             # Next.js app directory
    ├── components/      # React components
    ├── hooks/          # Custom React hooks
    ├── lib/            # Utilities
    └── package.json    # Node dependencies
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 or higher
- **Node.js**: 16.0 or higher
- **Tesseract OCR**: For scanned document processing
- **API Keys**: OpenAI or Azure OpenAI API credentials

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```
   This will:
   - Install all required dependencies
   - Create necessary directories
   - Generate a `.env` template file

3. **Configure environment variables**
   
   Edit the `.env` file with your API credentials:
   ```env
   # Choose provider: 'openai' or 'azure'
   PROVIDER=azure

   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_key_here

   # Azure OpenAI Configuration
   AZURE_API_KEY=your_azure_key_here
   AZURE_ENDPOINT=your_azure_endpoint_here
   AZURE_API_VERSION=2024-02-01
   AZURE_DEPLOYMENT_MODEL=gpt-4
   AZURE_DEPLOYMENT_NAME=your_deployment_name
   ```

4. **Start the backend server**
   ```bash
   python run.py
   ```
   The Dash application will be available at `http://127.0.0.1:8050`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```
   The Next.js application will be available at `http://localhost:3000`

4. **Build for production** (optional)
   ```bash
   npm run build
   npm start
   ```

## 📖 Usage

### Uploading Tender Documents

1. Open the application in your browser
2. Navigate to the **Upload** page
3. Drag and drop tender documents or click to browse
4. Supported formats: PDF, DOCX, DOC, TXT
5. Click **Process** to start extraction

### Viewing Dashboard

1. After processing, navigate to the **Dashboard**
2. View extracted tender information:
   - Tender ID and Title
   - Issuing Authority
   - Important Dates (Publication, Submission, Opening)
   - Financial Details (EMD, Tender Fee, Estimated Cost)
   - Eligibility Criteria
   - Location and Contact Information
3. Compare multiple tenders side-by-side
4. Sort and filter based on priority scores

### Using Chat Interface

1. Navigate to the **Chat** page
2. Select a processed tender from the dropdown
3. Ask questions about the tender:
   - "What is the submission deadline?"
   - "What are the eligibility criteria?"
   - "What documents are required?"
4. Get AI-powered intelligent responses based on the tender content

## 🔧 Configuration

### Backend Configuration

Edit `backend/app/config.py` to customize:

- **File paths**: Upload and extraction directories
- **LLM settings**: Enable/disable LLM extraction and evaluation
- **Processing options**: OCR settings, text cleaning rules

### Frontend Configuration

Edit `frontend/next.config.mjs` for:

- API endpoints
- Build configuration
- Environment variables

## 📦 Dependencies

### Backend
- **pdfplumber**, **pymupdf**: PDF processing
- **pytesseract**: OCR for scanned documents
- **docx2txt**: Word document extraction
- **dash**, **dash-bootstrap-components**: Web framework
- **openai**: LLM integration
- **chromadb**: Vector database
- **sentence-transformers**: Text embeddings
- **pandas**: Data manipulation
- **plotly**: Visualizations

### Frontend
- **Next.js 16**: React framework
- **Radix UI**: Accessible component library
- **TailwindCSS**: Utility-first CSS
- **lucide-react**: Icon library
- **recharts**: Chart library

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 🛠️ Development

### Adding New Extraction Fields

1. Update regex patterns in `backend/core/parser.py`
2. Modify LLM prompts in `backend/core/llm_client.py`
3. Update the data model in `backend/core/processor.py`

### Customizing UI Components

1. Modify layouts in `backend/app/layouts.py` (Dash UI)
2. Or edit React components in `frontend/components/` (Next.js UI)

## 🔒 Security Considerations

- **API Keys**: Never commit `.env` files to version control
- **File Uploads**: Validate and sanitize all uploaded files
- **User Input**: Implement proper input validation
- **CORS**: Configure appropriate CORS policies for production

## 📝 API Documentation

### Backend Endpoints

The Dash application uses callback-based architecture. Key endpoints include:

- **Upload Processing**: Handles file uploads and triggers processing
- **Dashboard Updates**: Provides processed tender data
- **Chat Interface**: Manages Q&A interactions with tender documents