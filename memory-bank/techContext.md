# Technical Context: Past Paper Concept Analyzer

## 1. Core Technologies

### PDF Processing
- **PyPDF2/PyMuPDF**: Python libraries for extracting text from PDF files
- **pdfplumber**: More robust text extraction with better layout preservation
- **Tesseract OCR**: For handling scanned papers that require OCR

### Language Processing
- **LangChain**: Framework for LLM integration and processing pipeline
- **OpenAI API**: Using GPT models for concept extraction and analysis
- **Hugging Face Transformers**: Alternative for local model execution

### Data Storage
- **SQLite**: Lightweight relational database for concept storage in development
- **PostgreSQL**: For production scaling if necessary
- **SQLAlchemy**: ORM for database interaction

### Backend
- **FastAPI**: API framework for the backend services
- **Pydantic**: For data validation and settings management
- **Python 3.10+**: Core programming language

### Frontend (Optional)
- **Streamlit**: For rapid dashboard development
- **Plotly/Matplotlib**: Data visualization of concept trends
- **React**: More sophisticated UI if needed

## 2. Development Environment

### Core Dependencies
- Python virtual environment (standard setup)
- Nix shell environment (NixOS users)
- PDF processing libraries
- Database connector
- LLM API access

### Development Tools
- Git for version control
- Black/isort for code formatting
- Pytest for testing
- Jupyter notebooks for experimentation
- Nix for reproducible development environments

## 3. Data Flow & Processing

```mermaid
flowchart LR
    PDF[PDF Files] --> PyPDF[PyPDF/pdfplumber]
    PyPDF --> RawText[Raw Text]
    RawText --> LangChain[LangChain]
    LangChain --> OpenAI[OpenAI API]
    OpenAI --> Concepts[Concept Extraction]
    Concepts --> SQLAlchemy[SQLAlchemy]
    SQLAlchemy --> Database[(Database)]
    Database --> FastAPI[FastAPI]
    FastAPI --> Streamlit[Streamlit Dashboard]
```

## 4. Technical Constraints

- **LLM API Cost**: Consider rate limiting and batching to control API costs
- **PDF Quality**: Need robust handling for different PDF formats/qualities
- **Model Context Limits**: Large papers may need chunking to fit context windows
- **Local Processing**: Consider options for running smaller models locally
