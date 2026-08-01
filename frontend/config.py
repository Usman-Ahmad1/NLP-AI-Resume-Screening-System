"""
Frontend configuration for Resume Screener.
"""

import os
from pathlib import Path

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# API Endpoints
ENDPOINTS = {
    "health": f"{API_BASE_URL}/health",
    "dataset_info": f"{API_BASE_URL}/dataset-info",
    "job_positions": f"{API_BASE_URL}/job-positions",
    "match_candidates": f"{API_BASE_URL}/match-candidates",
    "analyze_job": f"{API_BASE_URL}/analyze-job",
    "upload_pdf": f"{API_BASE_URL}/upload-pdf",
}

# App Settings
APP_TITLE = "AI Resume Screener"
APP_ICON = "📄"
APP_DESCRIPTION = "AI-powered resume screening and candidate matching system"

# Color Theme
COLORS = {
    "primary": "#6C63FF",
    "secondary": "#FF6B6B",
    "success": "#00B894",
    "warning": "#FDCB6E",
    "danger": "#E17055",
    "dark": "#2D3436",
    "light": "#F5F6FA",
    "white": "#FFFFFF",
}

# Display Settings
MAX_CANDIDATES_DISPLAY = 20
PAGE_SIZE = 10