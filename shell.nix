{ pkgs ? import <nixpkgs-unstable> {} }:
with pkgs; let
  my-python-packages = ps: with ps; [
    # Core dependencies
    sqlalchemy
    pypdf2
    pdfplumber
    python-dotenv
    pillow
    
    # Optional OCR dependencies
    pytesseract
    
    # Development tools
    pytest
    
    # These packages will be installed from nixpkgs
    # rather than pip (if available)
    langchain
    langchain-community
    openai
    pdf2image
  ];
  my-python = pkgs.python3.withPackages my-python-packages;
in
mkShell {
  buildInputs = [
    my-python
    pkgs.black
    pkgs.sqlitebrowser
    pkgs.ruff
    pkgs.isort
    
    # System dependencies
    tesseract    # For pytesseract
    poppler_utils # For pdf2image
  ];
  
  # Environment variables
  shellHook = ''
    echo "Python development environment for Past Paper Concepts activated"
    
    # Make the Python interpreter available in the shell
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    
    # Set environment variables for OCR if needed
    export TESSDATA_PREFIX=${pkgs.tesseract}/share/tessdata
  '';
}
