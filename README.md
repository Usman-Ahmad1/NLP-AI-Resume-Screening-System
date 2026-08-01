# 📄 AI Resume Screener

An AI-powered resume screening system that automatically matches candidates to job positions using NLP and semantic similarity.

---

## 🎯 Problem

**Manual resume screening is time-consuming and inconsistent.**

HR teams spend hours reviewing hundreds of resumes for a single position, leading to:
- ⏱️ **Slow hiring cycles** - weeks spent filtering candidates
- 🎯 **Inconsistent evaluations** - different reviewers, different standards
- 💰 **Missed talent** - great candidates overlooked due to manual bias
- 📊 **No data-driven insights** - decisions based on gut feeling

---

## 💡 Solution

**AI-powered resume screening that ranks candidates objectively.**

This system uses Natural Language Processing (NLP) and semantic search to:
- ✅ **Extract** key information (skills, experience, education) from resumes
- ✅ **Match** candidates to job requirements using hybrid scoring
- ✅ **Rank** candidates objectively based on skill fit, experience, and semantic similarity
- ✅ **Explain** why each candidate scored well (matching/missing skills)

---

## 🚀 Features

- 📄 **PDF Resume Extraction** - Upload resumes, extract text automatically
- 🎯 **Hybrid Matching** - Combines keyword search + semantic similarity
- 📊 **Transparent Scoring** - See skill, experience, education, and semantic scores
- 🏆 **Candidate Ranking** - Top candidates ranked by overall fit
- 📈 **Data Analytics** - Visualize job positions and candidate distribution
- 🌐 **REST API** - Easy integration with existing systems
- 💻 **Interactive Dashboard** - Streamlit frontend for HR teams

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11 |
| **NLP** | spaCy, Sentence-Transformers |
| **ML** | scikit-learn, NumPy, Pandas |
| **PDF Processing** | pdfplumber, PyMuPDF |
| **Database** | SQLite (dev) → PostgreSQL (production) |
| **Frontend** | Streamlit |
| **Deployment** | Docker, Render/Railway |

---

