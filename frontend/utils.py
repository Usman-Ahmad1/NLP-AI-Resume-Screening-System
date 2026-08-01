"""
Utility functions for the frontend.
"""

import requests
import pandas as pd
import streamlit as st
from datetime import datetime
import re

def format_score(score: float) -> str:
    """Format a score as percentage."""
    if score is None:
        return "0%"
    return f"{score * 100:.1f}%"

def format_experience(years: float) -> str:
    """Format experience years."""
    if years is None or years == 0:
        return "No experience"
    if years < 1:
        return f"{int(years * 12)} months"
    if years < 2:
        return "1 year"
    return f"{int(years)} years"

def get_score_color(score: float) -> str:
    """Get color based on score."""
    if score >= 0.8:
        return "🟢"  # Green
    elif score >= 0.6:
        return "🟡"  # Yellow
    elif score >= 0.4:
        return "🟠"  # Orange
    else:
        return "🔴"  # Red

def get_score_label(score: float) -> str:
    """Get label based on score."""
    if score >= 0.8:
        return "Excellent Match"
    elif score >= 0.6:
        return "Good Match"
    elif score >= 0.4:
        return "Moderate Match"
    else:
        return "Low Match"

def safe_request(url: str, method: str = "GET", **kwargs):
    """Make a safe HTTP request."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, **kwargs, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, **kwargs, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Is the server running?")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def extract_skills_from_text(text: str) -> list:
    """Extract skills from text using common patterns."""
    if not text:
        return []
    
    # Common technical skills (expandable)
    common_skills = [
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
        "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git",
        "machine learning", "deep learning", "nlp", "computer vision",
        "data science", "analytics", "statistics", "ai", "rag", "langchain",
        "excel", "power bi", "tableau", "looker", "spark", "hadoop", "kafka"
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in common_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            found_skills.append(skill)
    
    return list(set(found_skills))