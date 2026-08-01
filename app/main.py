"""
FastAPI application entry point for Resume Screener.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile

from app.config import settings
from app.core.logging_config import logger
from app.services.pdf_extractor import PDFExtractor, clean_extracted_text
from app.services.enhanced_processor import EnhancedResumeProcessor

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered Resume Screening System",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pdf_extractor = PDFExtractor()
enhanced_processor = EnhancedResumeProcessor("resume_data.csv")


# ==================== HEALTH & ROOT ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health"
    }


# ==================== PDF EXTRACTION ENDPOINTS ====================

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and extract its text content."""
    if not file.filename.lower().endswith(('.pdf')):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    temp_file = None
    temp_path = None
    
    try:
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(content)
        temp_file.flush()
        temp_path = Path(temp_file.name)
        
        logger.info(f"Processing PDF: {file.filename} ({file_size} bytes)")
        result = pdf_extractor.extract(temp_path)
        
        if not result.extraction_success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract text: {result.error}"
            )
        
        cleaned_text = clean_extracted_text(result.text)
        
        return {
            "filename": file.filename,
            "file_size_bytes": file_size,
            "page_count": result.page_count,
            "extraction_method": result.method,
            "metadata": result.metadata,
            "text": cleaned_text,
            "text_length": len(cleaned_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        if temp_file:
            temp_file.close()
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except:
                pass


# ==================== OLLAMA ENDPOINT ====================

@app.get("/test-ollama")
async def test_ollama():
    """Test Ollama connection."""
    if not settings.OLLAMA_ENABLED:
        return {"status": "disabled", "message": "Ollama is not enabled"}
    
    try:
        import ollama
        client = ollama.Client(host=settings.OLLAMA_API_BASE)
        response = client.generate(
            model=settings.OLLAMA_MODEL,
            prompt="Hello, are you working?"
        )
        return {
            "status": "connected",
            "model": settings.OLLAMA_MODEL,
            "response": response["response"][:100] + "..."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not connect to Ollama: {str(e)}"
        }


# ==================== DATASET ENDPOINTS ====================

@app.get("/dataset-info")
async def get_dataset_info():
    """Get information about the dataset."""
    try:
        enhanced_processor.load_data()
        df = enhanced_processor.df
        
        positions = {}
        job_col = enhanced_processor.column_mappings.get('job_position', 'job_position_name')
        if job_col in df.columns:
            positions = df[job_col].value_counts().head(10).to_dict()
        
        return {
            "total_resumes": len(df),
            "columns": df.columns.tolist(),
            "sample_job_positions": positions,
            "has_skills": int(df['skills'].notna().sum()),
            "has_education": int(df['educational_institution_name'].notna().sum()),
            "has_experience": int(df['professional_company_names'].notna().sum())
        }
    except Exception as e:
        logger.error(f"Error getting dataset info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job-positions")
async def get_job_positions():
    """Get all unique job positions."""
    try:
        enhanced_processor.load_data()
        positions = enhanced_processor.get_all_job_positions()
        return {
            "total_positions": len(positions),
            "positions": dict(list(positions.items())[:20])
        }
    except Exception as e:
        logger.error(f"Error getting job positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MATCHING ENDPOINTS ====================

@app.post("/match-candidates")
async def match_candidates(
    job_position: str,
    limit: int = 10
):
    """Find top candidates for a job position."""
    try:
        enhanced_processor.load_data()
        results = enhanced_processor.get_top_candidates_for_job(job_position, limit)
        
        formatted_results = []
        for r in results:
            try:
                match_scores = r.get('match_scores', {})
                candidate_features = r.get('candidate_features', {})
                
                formatted_results.append({
                    'candidate_index': r.get('candidate_index', 0),
                    'total_score': float(match_scores.get('total_score', 0)),
                    'score_breakdown': {
                        'skills': float(match_scores.get('score_breakdown', {}).get('skills', 0)),
                        'experience': float(match_scores.get('score_breakdown', {}).get('experience', 0)),
                        'education': float(match_scores.get('score_breakdown', {}).get('education', 0)),
                        'semantic': float(match_scores.get('score_breakdown', {}).get('semantic', 0))
                    },
                    'matching_skills': match_scores.get('matching_skills', [])[:10],
                    'missing_skills': match_scores.get('missing_skills', [])[:10],
                    'experience_years': float(candidate_features.get('experience_years', 0)),
                    'skills': candidate_features.get('skills', [])[:10],
                    'top_education': candidate_features.get('education', {}).get('degrees', [])[:2],
                    'dataset_match_score': float(r.get('matched_score', 0))
                })
            except Exception as e:
                print(f"Error formatting result: {e}")
                continue
        
        return {
            'job_position': job_position,
            'total_candidates_matched': len(results),
            'top_candidates': formatted_results
        }
    except Exception as e:
        logger.error(f"Error matching candidates: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-job")
async def analyze_job(job_position: str):
    """Analyze job requirements for a position."""
    try:
        enhanced_processor.load_data()
        
        job_col = enhanced_processor.column_mappings.get('job_position', 'job_position_name')
        matching_jobs = enhanced_processor.df[
            enhanced_processor.df[job_col].str.contains(job_position, case=False, na=False)
        ]
        
        if len(matching_jobs) == 0:
            return {"message": f"No jobs found for position: {job_position}"}
        
        job = matching_jobs.iloc[0]
        skills_required = enhanced_processor._safe_list(job.get('skills_required', []))
        
        return {
            'position': str(job.get(job_col, '')),
            'education_requirements': str(job.get('educationaL_requirements', '')),
            'experience_requirements': str(job.get('experiencere_requirement', '')),
            'skills_required': skills_required[:20],
            'total_skills_required': len(skills_required),
            'responsibilities_preview': str(job.get('responsibilities.1', ''))[:500],
            'has_experience_requirement': bool(job.get('experiencere_requirement'))
        }
    except Exception as e:
        logger.error(f"Error analyzing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc) if settings.DEBUG else None
        }
    )


# ==================== STARTUP/SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Actions to perform on application startup."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    if settings.OLLAMA_ENABLED:
        logger.info(f"Ollama enabled with model: {settings.OLLAMA_MODEL}")
    else:
        logger.info("Ollama disabled, using rule-based extraction")
    
    try:
        enhanced_processor.load_data()
        logger.info(f"✅ Loaded {len(enhanced_processor.df)} resumes")
    except Exception as e:
        logger.warning(f"⚠️ Could not pre-load dataset: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Actions to perform on application shutdown."""
    logger.info(f"Shutting down {settings.APP_NAME}")