"""
PDF text extraction service with multiple backend options.

This module provides robust PDF text extraction with support for:
- Digital PDFs (pdfplumber, PyMuPDF, pypdf)
- Layout detection
- Multi-column handling
- Fallback strategies
"""

import io
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

import pdfplumber
import fitz  # PyMuPDF
from pypdf import PdfReader
from loguru import logger
from pydantic import BaseModel, Field


class ExtractionMethod(str, Enum):
    """Supported PDF extraction backends."""
    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf" 
    PYPDF = "pypdf"
    HYBRID = "hybrid"


class ExtractionResult(BaseModel):
    """Result of PDF text extraction."""
    text: str
    pages: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    method: str
    page_count: int
    extraction_success: bool = True
    error: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class PDFExtractor:
    """
    PDF text extraction service supporting multiple backends.
    
    Features:
    - Multiple extraction methods with fallback
    - Page-by-page extraction
    - Metadata extraction
    - Layout preservation (column handling)
    """
    
    def __init__(
        self,
        preferred_method: ExtractionMethod = ExtractionMethod.HYBRID,
        fallback_enabled: bool = True
    ):
        """
        Initialize PDF extractor.
        
        Args:
            preferred_method: Primary extraction method
            fallback_enabled: Whether to try fallback methods on failure
        """
        self.preferred_method = preferred_method
        self.fallback_enabled = fallback_enabled
        self.logger = logger.bind(service="pdf_extractor")
        
    def extract(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ExtractionResult with text and metadata
        """
        self.logger.info(f"Extracting text from {file_path}")
        
        # Try preferred method first
        methods_to_try = self._get_methods_to_try()
        
        for method in methods_to_try:
            try:
                result = self._extract_with_method(file_path, method)
                if result.extraction_success and result.text.strip():
                    self.logger.info(f"Successfully extracted with {method}")
                    return result
            except Exception as e:
                self.logger.warning(f"Method {method} failed: {str(e)}")
                continue
        
        # All methods failed
        return ExtractionResult(
            text="",
            pages=[],
            metadata={},
            method="none",
            page_count=0,
            extraction_success=False,
            error="All extraction methods failed"
        )
    
    def _get_methods_to_try(self) -> List[str]:
        """Get ordered list of extraction methods to try."""
        if self.preferred_method == ExtractionMethod.HYBRID:
            return ["pdfplumber", "pymupdf", "pypdf"]
        return [self.preferred_method.value]
    
    def _extract_with_method(
        self,
        file_path: Path,
        method: str
    ) -> ExtractionResult:
        """Extract using specified method."""
        if method == "pdfplumber":
            return self._extract_pdfplumber(file_path)
        elif method == "pymupdf":
            return self._extract_pymupdf(file_path)
        elif method == "pypdf":
            return self._extract_pypdf(file_path)
        else:
            raise ValueError(f"Unknown extraction method: {method}")
    
    def _extract_pdfplumber(self, file_path: Path) -> ExtractionResult:
        """
        Extract using pdfplumber (best for layout-aware extraction).
        
        Advantages:
        - Good table detection
        - Layout preservation
        - Handles multi-column layouts well
        """
        pages = []
        full_text = []
        metadata = {}
        
        with pdfplumber.open(file_path) as pdf:
            metadata = pdf.metadata or {}
            
            for page in pdf.pages:
                # Extract text with layout preservation
                text = page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False
                )
                
                if text:
                    pages.append(text)
                    full_text.append(text)
        
        return ExtractionResult(
            text="\n\n".join(full_text),
            pages=pages,
            metadata=metadata,
            method="pdfplumber",
            page_count=len(pages)
        )
    
    def _extract_pymupdf(self, file_path: Path) -> ExtractionResult:
        """
        Extract using PyMuPDF (fast with good formatting).
        
        Advantages:
        - Very fast
        - Good text extraction
        - Handles Unicode well
        """
        pages = []
        full_text = []
        metadata = {}
        
        doc = fitz.open(file_path)
        metadata = doc.metadata
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            if text:
                pages.append(text)
                full_text.append(text)
        
        doc.close()
        
        return ExtractionResult(
            text="\n\n".join(full_text),
            pages=pages,
            metadata=metadata,
            method="pymupdf",
            page_count=len(pages)
        )
    
    def _extract_pypdf(self, file_path: Path) -> ExtractionResult:
        """
        Extract using pypdf (simple, pure Python).
        
        Advantages:
        - No external dependencies
        - Simple implementation
        - Works for most simple PDFs
        """
        pages = []
        full_text = []
        metadata = {}
        
        reader = PdfReader(file_path)
        metadata = reader.metadata or {}
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
                full_text.append(text)
        
        return ExtractionResult(
            text="\n\n".join(full_text),
            pages=pages,
            metadata=metadata,
            method="pypdf",
            page_count=len(pages)
        )
    
    def extract_batch(self, file_paths: List[Path]) -> List[ExtractionResult]:
        """
        Extract text from multiple PDFs.
        
        Args:
            file_paths: List of PDF file paths
            
        Returns:
            List of ExtractionResults
        """
        results = []
        for file_path in file_paths:
            result = self.extract(file_path)
            results.append(result)
        return results


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text for better NLP processing.
    
    Basic cleaning without over-processing:
    - Normalize whitespace
    - Remove excessive newlines
    - Standardize common characters
    """
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newline
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Normalize common Unicode characters
    text = text.replace('–', '-').replace('—', '-')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    
    return text.strip()