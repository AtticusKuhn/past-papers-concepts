# Past Paper Concept Analyzer

A system for analyzing Cambridge Computer Science Tripos past papers to extract, store, and analyze key concepts and themes.

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
5. Configure your `.env` file with required API keys
6. Place PDF files in the `pdfs/` directory
7. Run the pipeline: `python process_papers.py`
8. Query concepts: `python query_concepts.py`

#### Option 2: NixOS Setup

1. Clone this repository
2. Configure your `.env` file with required API keys
3. Enter the development environment: `nix-shell`
4. Place PDF files in the `pdfs/` directory
5. Run the pipeline: `python process_papers.py`
6. Query concepts: `python query_concepts.py`

## Project Structure

```
pastpaper_concepts/
├── pdfs/                  # Source PDF files
├── extracted/             # Extracted text files
├── db/                    # Database files
├── paper_ingestor.py      # Paper ingestion module
├── pdf_processor.py       # PDF processing module
├── text_analyzer.py       # LLM-based text analysis
├── concept_storage.py     # Database operations
├── query_engine.py        # Analysis and querying
├── models/                # Data models
├── utils/                 # Utility functions
├── prompts/               # LLM prompt templates
├── config.py              # Configuration management
├── process_papers.py      # Pipeline execution script
├── query_concepts.py      # Concept querying script
└── tests/                 # Test suite
```

## Contribution & Development

This project follows the patterns and preferences outlined in `.clinerules`.
