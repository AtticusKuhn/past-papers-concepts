# Past Paper Concept Analyzer

A system for analyzing Cambridge Computer Science Tripos past papers to extract, store, and analyze key concepts and themes.

## Overview

The Past Paper Concept Analyzer is a comprehensive tool designed to analyze Cambridge Computer Science Tripos examination papers, extracting key computer science concepts and storing them in a structured database. This enables students, educators, and researchers to identify recurring themes, important topics, and changes in focus over time.

## Project Architecture: Event-Driven Processing Pipeline

This project implements an event-driven processing pipeline architecture optimized for analyzing academic papers. This architecture was chosen specifically to address the unique challenges of processing examination papers with varying formats, extracting concepts using LLMs, and providing reliable analysis capabilities.

### Architecture Overview

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌─────────┐
│  Paper  │    │   PDF    │    │   Text   │    │  Concept  │    │  Query  │
│ Ingestor│───▶│Processor │───▶│ Analyzer │───▶│  Storage  │◀───│ Engine  │
└─────────┘    └──────────┘    └──────────┘    └───────────┘    └─────────┘
                    ▲               ▲                               ▲
                    │               │                               │
                ┌───────┐       ┌───────┐                      ┌───────┐
                │  PDF  │       │  LLM  │                      │  UI   │
                │Library│       │Service│                      │ Layer │
                └───────┘       └───────┘                      └───────┘
```

### Why This Architecture Is Optimal

1. **Decoupling & Modularity**
   - Each component operates independently with clear interfaces
   - Components can be developed, tested, and scaled separately
   - New paper formats or LLM providers can be integrated without system-wide changes

2. **Resilience & Fault Tolerance**
   - Failures in one component don't cascade to others
   - Processing can be resumed from intermediate states
   - Each paper's processing is isolated from others

3. **Scalability**
   - Components can be scaled independently based on resource needs
   - The system handles both single papers and large batches efficiently
   - Resource-intensive operations (like LLM API calls) can be optimized separately

4. **Adaptability**
   - Different PDF extraction strategies can be applied based on paper format
   - LLM prompts can be refined without affecting other components
   - Storage mechanisms can evolve as data grows

### Core Components Explained

#### 1. Paper Ingestor

**Purpose**: Manages the intake of PDF papers and initializes the processing pipeline.

**Key Features**:
- Paper validation and metadata extraction (year, course, paper number)
- Processing queue management
- Duplicate detection
- Processing status tracking

**Implementation Considerations**:
- File watching for automatic processing of new papers
- Paper metadata extraction from filenames or contents
- Event emission to trigger PDF processing

#### 2. PDF Processor

**Purpose**: Extracts text content from PDF files with high fidelity.

**Key Features**:
- Text extraction with layout preservation
- OCR integration for scanned papers
- Structural analysis (questions, sections)
- Pre-processing for LLM consumption

**Implementation Considerations**:
- Multiple extraction strategies based on PDF quality
- Fallback mechanisms when primary extraction fails
- Text chunking to manage large documents

#### 3. Text Analyzer

**Purpose**: Leverages LLMs to identify key concepts, terms, and themes.

**Key Features**:
- LLM prompt engineering for concept extraction
- Context management for large documents
- Concept categorization and relation mapping
- Citation tracking to original text

**Implementation Considerations**:
- Rate limiting and batching for API efficiency
- Prompt optimization for consistent results
- Fallback to simpler models when appropriate

#### 4. Concept Storage

**Purpose**: Persistently stores extracted concepts with proper indexing and relationships.

**Key Features**:
- Structured schema for concepts, terms, and citations
- Relationship modeling between concepts
- Efficient querying capabilities
- Metadata association (paper, year, question)

**Implementation Considerations**:
- SQLite for development simplicity
- Migration path to PostgreSQL for scaling
- Proper indexing for performance
- Versioning of concept extractions

#### 5. Query Engine

**Purpose**: Provides powerful retrieval and analysis capabilities.

**Key Features**:
- Concept frequency analysis
- Temporal trend identification
- Subject area clustering
- Concept co-occurrence analysis

**Implementation Considerations**:
- SQL query optimization
- Caching of common queries
- Flexible filtering options
- Export capabilities

### Data Flow

1. Paper PDF files are placed in the `pdfs/` directory
2. The Paper Ingestor validates and registers the paper
3. The PDF Processor extracts text and saves to `extracted/`
4. The Text Analyzer processes text chunks through the LLM
5. Extracted concepts are stored in the database
6. The Query Engine allows analysis of stored concepts

### Database Schema

```
┌───────────────┐       ┌────────────────┐       ┌────────────────┐
│     Paper     │       │    Concept     │       │  Occurrence    │
├───────────────┤       ├────────────────┤       ├────────────────┤
│ id            │       │ id             │       │ id             │
│ year          │◀─────┼─paper_id       │◀─────┼─concept_id      │
│ course        │       │ name           │       │ paper_id       │
│ paper_number  │       │ category       │       │ question       │
│ filename      │       │ description    │       │ context        │
│ processed_at  │       │ parent_concept │       │ confidence     │
└───────────────┘       └────────────────┘       └────────────────┘
                                │                        
                                ▼                        
                        ┌────────────────┐               
                        │ ConceptRelation│               
                        ├────────────────┤               
                        │ id             │               
                        │ concept1_id    │               
                        │ concept2_id    │               
                        │ relation_type  │               
                        │ strength       │               
                        └────────────────┘               
```

### Implementation Advantages

1. **Incremental Processing**
   - New papers can be added at any time
   - Processing can be paused and resumed
   - Results are available as soon as individual papers complete

2. **Cost Management**
   - LLM API calls can be batched and rate-limited
   - Only changed/new papers need processing
   - Caching strategies reduce repeated analysis

3. **Quality Control**
   - Each component has clear success criteria
   - Errors in one paper don't affect others
   - Continuous refinement of extraction techniques

4. **Extensibility**
   - New analysis types can be added (e.g., citation networks)
   - Additional metadata can be captured
   - Interface options can evolve independently

### Getting Started

#### Option 1: Standard Setup (non-NixOS)

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.sample` to `.env` and configure your API keys
6. Place PDF files in the `pdfs/` directory
7. Run the pipeline with all steps: `python process_papers.py`
8. Query concepts: `python query_engine.py`

#### Option 2: NixOS Setup

1. Clone this repository
2. Copy `.env.sample` to `.env` and configure your API keys
3. Enter the development environment: `nix-shell`
4. Place PDF files in the `pdfs/` directory
5. Run the pipeline: `python process_papers.py`
6. Query concepts: `python query_engine.py`

### Command Line Usage

The main processing script (`process_papers.py`) offers various command-line options:

```
usage: process_papers.py [-h] [--steps {ingest,extract,analyze} [{ingest,extract,analyze} ...]] [--limit LIMIT] [--pdf-only] [--skip-extraction]

Process past papers and extract concepts

options:
  -h, --help            show this help message and exit
  --steps {ingest,extract,analyze} [{ingest,extract,analyze} ...]
                        Specific steps to run (default: all steps)
  --limit LIMIT         Maximum number of papers to process
  --pdf-only            Only process PDFs without analyzing them
  --skip-extraction     Skip PDF text extraction, only run analysis
```

Examples:

- Process everything: `python process_papers.py`
- Only register new papers: `python process_papers.py --steps ingest`
- Only extract text from PDFs: `python process_papers.py --steps extract --pdf-only`
- Only analyze PDFs that are already processed: `python process_papers.py --steps analyze --skip-extraction`
- Process only 2 papers: `python process_papers.py --limit 2`

## Project Structure

```
pastpaper_concepts/
├── pdfs/                  # Source PDF files
├── extracted/             # Extracted text files (JSON)
├── db/                    # Database files
├── logs/                  # Log files directory
├── models/                # Data models
│   ├── __init__.py
│   ├── base.py            # SQLAlchemy base configuration
│   ├── concept.py         # Concept models
│   └── paper.py           # Paper model
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── db.py              # Database utilities
│   ├── llm.py             # LLM integration utilities
│   ├── logging_config.py  # Centralized logging configuration
│   └── pdf.py             # PDF processing utilities
├── prompts/               # LLM prompt templates
│   └── concept_extraction.md  # Concept extraction prompt
├── config.py              # Application configuration
├── paper_ingestor.py      # Paper discovery and registration
├── pdf_processor.py       # PDF text extraction
├── text_analyzer.py       # LLM-based concept extraction
├── query_engine.py        # Concept querying and analysis
├── process_papers.py      # Main processing pipeline
├── .env.sample            # Sample environment variables
├── .env                   # Environment variables (not in VCS)
├── requirements.txt       # Python dependencies
└── shell.nix              # Nix environment definition
```

## Key Components

### Utilities (`utils/`)

The utilities package provides reusable functionality across the application:

- **db.py**: Database connection management, transaction handling, and helper functions
- **logging_config.py**: Centralized logging configuration for consistent logging across components
- **pdf.py**: PDF text extraction with multiple methods and fallback strategies
- **llm.py**: LLM integration with prompt management and response parsing

### Models (`models/`)

The models package defines the SQLAlchemy ORM models for the database:

- **base.py**: SQLAlchemy Base class and session utilities
- **concept.py**: Models for concepts, relationships, and occurrences 
- **paper.py**: Model for paper metadata

### Processing Pipeline

- **paper_ingestor.py**: Discovers and registers new papers from the pdfs/ directory
- **pdf_processor.py**: Extracts text from PDFs using various methods with fallbacks
- **text_analyzer.py**: Analyzes text using LLMs to identify and extract concepts
- **process_papers.py**: Orchestrates the complete processing pipeline

### Analysis and Querying

- **query_engine.py**: Provides methods to query and analyze extracted concepts

## Features

### Robust PDF Processing

- Multiple extraction methods (pdfplumber, PyPDF2)
- OCR support for scanned papers
- Text preprocessing for better LLM analysis
- Fallback mechanisms for handling extraction failures

### Advanced LLM Integration

- Prompt template management
- Response validation and normalization
- Error handling and recovery
- Deduplication of extracted concepts

### Comprehensive Logging

- Component-specific log files
- Configurable log levels
- Detailed error tracking
- Performance monitoring

### Flexible Processing Pipeline

- Modular architecture with distinct processing phases
- Configurable processing steps
- Batch processing with rate limiting
- Error handling and recovery at each step

### Rich Query Capabilities

- Concept frequency analysis
- Year-by-year trends
- Related concept discovery
- Context-aware concept searching

## Configuration

The application is configured through environment variables, which can be set in a `.env` file:

```
# Database configuration
DATABASE_URL=sqlite:///db/concepts.db

# LLM configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=8192
OPENAI_TEMPERATURE=0.0

# OCR configuration (optional)
OCR_ENABLED=false
TESSERACT_PATH=/path/to/tesseract

# Logging
LOG_LEVEL=INFO
```

## Contribution & Development

This project follows the patterns and preferences outlined in `.clinerules`. Key development guidelines include:

- **Code Style**: Follow PEP 8 guidelines with type hints
- **Documentation**: Maintain comprehensive docstrings and update README as needed
- **Testing**: Add tests for new functionality
- **Error Handling**: Use proper exception handling and logging
- **Modularity**: Keep components decoupled and focused on single responsibilities

## License

[Add appropriate license information here]
