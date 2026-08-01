"""
Unit tests for PDF extraction service.
"""

import pytest
from pathlib import Path
from app.services.pdf_extractor import PDFExtractor, ExtractionMethod


@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file for testing."""
    from reportlab.pdfgen import canvas
    import io
    
    # This creates a simple PDF for testing
    # In practice, you'd use a real PDF file
    
    return None  # Placeholder - we'll add actual PDFs later


def test_pdf_extractor_initialization():
    """Test PDFExtractor initialization."""
    extractor = PDFExtractor()
    assert extractor.preferred_method == ExtractionMethod.HYBRID
    assert extractor.fallback_enabled is True


def test_clean_extracted_text():
    """Test text cleaning function."""
    from app.services.pdf_extractor import clean_extracted_text
    
    test_text = "This  has   extra    whitespace\n\nand newlines."
    cleaned = clean_extracted_text(test_text)
    assert "  " not in cleaned
    assert cleaned == "This has extra whitespace and newlines."


# Integration test (requires actual PDF)
@pytest.mark.integration
def test_pdf_extraction_integration():
    """Test PDF extraction with a real PDF file."""
    # This test would need a real PDF file
    pass