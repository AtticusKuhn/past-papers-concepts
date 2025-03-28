# Active Context: Past Paper Concept Analyzer

## Current Focus

We are in the initial planning and architecture design phase of the project. The focus is on:

1. Establishing a robust architecture that can process PDF files and extract concepts
2. Designing a database schema that captures concepts with proper citations
3. Determining the optimal approach for LLM integration

## Recent Decisions

1. **Pipeline Architecture**: We've opted for a modular pipeline approach to:
   - Allow independent processing of each exam paper
   - Enable incremental addition of new papers
   - Support easy replacement/upgrade of individual components

2. **Database-Centric Design**: 
   - A structured database will be the system's core
   - All extracted concepts will be properly associated with their source papers
   - This enables powerful querying and trend analysis

3. **LLM Integration Strategy**:
   - Using LangChain for LLM orchestration
   - Designing specific prompts for concept extraction
   - Removed text chunking for exam papers

4. **Development Environment Enhancement**:
   - Added Nix support through shell.nix for NixOS users
   - Maintained compatibility with traditional venv-based workflows
   - Ensures consistent development environment across different systems

5. **Full Document Processing with Smart Fallback**:
   - Switched to processing entire PDF content at once, removing chunking by default
   - Rationale: Exam papers are small (max 3 pages) and fit within LLM context windows
   - Added token estimation to detect potential context limit issues
   - Implemented automatic fallback to chunking for documents exceeding safe token limits
   - Enhanced error handling to provide clear guidance on context window issues
   - Benefits: Simplifies processing pipeline while ensuring robustness for larger documents

## Next Steps

Immediate priorities:

1. Create a basic project structure with essential components
2. Implement a PDF text extraction proof-of-concept
3. Design and implement the database schema
4. Develop initial LLM prompts for concept extraction
5. Build simple query mechanisms for concept retrieval

## Open Questions

1. How to handle scanned PDFs that may require OCR?
2. How to balance cost and performance when using commercial LLM APIs?
3. What level of user interface is appropriate for this project?
4. Should we consider retaining chunks for specific use cases or documents that might require finer-grained analysis?
