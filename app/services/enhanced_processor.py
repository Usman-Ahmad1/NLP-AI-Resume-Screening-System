"""
Enhanced Resume Processor for structured Kaggle dataset.
Handles BOM characters and column name variations automatically.
Includes caching for fast matching.
"""

import pandas as pd
import json
import re
import pickle
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from collections import Counter

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    cosine_similarity = None


class EnhancedResumeProcessor:
    """
    Process structured resume data from Kaggle with advanced matching.
    Includes caching for fast repeated queries.
    """
    
    def __init__(self, dataset_path: str = "resume_data.csv"):
        self.dataset_path = Path(dataset_path)
        self.df = None
        self.logger = logger
        self.column_mappings = {}
        self._embeddings_cache = None
        
        # Load embedding model
        self.embedding_model = None
        if SentenceTransformer is not None:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Embedding model loaded")
            except Exception as e:
                print(f"⚠️ Embedding model not loaded: {e}")
    
    def _get_cache_dir(self) -> Path:
        """Get the cache directory path."""
        cache_dir = Path("data/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def _get_embedding_cache_path(self) -> Path:
        """Get the path for cached embeddings."""
        return self._get_cache_dir() / "embeddings_cache.pkl"
    
    def _get_dataset_hash(self) -> str:
        """Get a hash of the dataset for cache invalidation."""
        if self.df is None:
            self.load_data()
        # Use number of rows and columns as a simple hash
        return f"{len(self.df)}_{len(self.df.columns)}"
    
    def _load_cached_embeddings(self) -> Optional[Dict]:
        """Load cached embeddings from disk."""
        cache_path = self._get_embedding_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached = pickle.load(f)
                    # Check if cache is for the current dataset
                    if cached.get('dataset_hash') == self._get_dataset_hash():
                        print(f"✅ Loaded {len(cached.get('embeddings', {}))} cached embeddings")
                        return cached.get('embeddings', {})
                    else:
                        print("⚠️ Cache is for different dataset, recomputing...")
            except Exception as e:
                print(f"⚠️ Could not load cache: {e}")
        return None
    
    def _save_cached_embeddings(self, embeddings: Dict):
        """Save embeddings to cache."""
        cache_path = self._get_embedding_cache_path()
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'dataset_hash': self._get_dataset_hash(),
                    'embeddings': embeddings
                }, f)
            print(f"✅ Saved {len(embeddings)} embeddings to cache")
        except Exception as e:
            print(f"⚠️ Could not save cache: {e}")
    
    def load_data(self) -> pd.DataFrame:
        """Load the structured dataset."""
        try:
            self.df = pd.read_csv(self.dataset_path, encoding='utf-8-sig')
            self.df.columns = self.df.columns.str.strip()
            
            print(f"✅ Loaded {len(self.df)} structured resumes")
            self._detect_column_mappings()
            
            # Parse string lists
            list_columns = ['skills', 'skills_required', 'responsibilities']
            for col in list_columns:
                if col in self.df.columns:
                    self.df[col] = self.df[col].apply(
                        lambda x: eval(x) if isinstance(x, str) and x.startswith('[') else x
                    )
            
            return self.df
        except Exception as e:
            print(f"❌ Failed to load: {str(e)}")
            raise
    
    def _detect_column_mappings(self):
        """Auto-detect column name variations."""
        columns = [col.strip() for col in self.df.columns.tolist()]
        
        # Map column names
        for col in columns:
            if 'job_position_name' in col.lower():
                self.column_mappings['job_position'] = col
            elif 'skills_required' in col.lower():
                self.column_mappings['skills_required'] = col
            elif 'educationaL_requirements' in col.lower():
                self.column_mappings['education_requirements'] = col
            elif 'experiencere_requirement' in col.lower():
                self.column_mappings['experience_requirements'] = col
            elif 'responsibilities.1' in col.lower():
                self.column_mappings['responsibilities'] = col
            elif 'matched_score' in col.lower():
                self.column_mappings['matched_score'] = col
        
        # Set defaults for missing mappings
        self.column_mappings.setdefault('job_position', 'job_position_name')
        self.column_mappings.setdefault('skills_required', 'skills_required')
        self.column_mappings.setdefault('education_requirements', 'educationaL_requirements')
        self.column_mappings.setdefault('experience_requirements', 'experiencere_requirement')
        self.column_mappings.setdefault('responsibilities', 'responsibilities.1')
        self.column_mappings.setdefault('matched_score', 'matched_score')
    
    def _safe_str(self, value) -> str:
        """Safely convert any value to string, handling numpy arrays."""
        if value is None:
            return ""
        if isinstance(value, (np.ndarray, pd.Series)):
            if value.size == 0:
                return ""
            try:
                value = value.item() if value.size == 1 else value.tolist()
            except:
                pass
        if isinstance(value, list):
            return " ".join(str(v) for v in value if v)
        try:
            if pd.isna(value):
                return ""
        except:
            pass
        return str(value)
    
    def _safe_list(self, value) -> List:
        """Safely convert any value to list, handling numpy arrays and strings."""
        if value is None:
            return []
        
        # Handle pandas NA/NaN
        try:
            if pd.isna(value):
                return []
        except:
            pass
        
        # Handle numpy arrays
        if isinstance(value, np.ndarray):
            if value.size == 0:
                return []
            return value.tolist()
        
        # Handle pandas Series
        if isinstance(value, pd.Series):
            return value.tolist()
        
        # Already a list
        if isinstance(value, list):
            return value
        
        # String that looks like a list
        if isinstance(value, str):
            if value.startswith('[') and value.endswith(']'):
                try:
                    result = eval(value)
                    if isinstance(result, list):
                        return result
                except:
                    pass
            return [value] if value.strip() else []
        
        return [value] if value else []
    
    def extract_candidate_features(self, row: pd.Series) -> Dict[str, Any]:
        """Extract all features from a candidate's resume."""
        
        # Skills
        skills = self._safe_list(row.get('skills', []))
        
        # Education
        education = {
            "institutions": self._safe_list(row.get('educational_institution_name', [])),
            "degrees": self._safe_list(row.get('degree_names', [])),
            "years": self._safe_list(row.get('passing_years', [])),
            "fields": self._safe_list(row.get('major_field_of_studies', []))
        }
        
        # Experience
        start_dates_raw = row.get('start_dates', [])
        end_dates_raw = row.get('end_dates', [])
        
        experience = {
            "companies": self._safe_list(row.get('professional_company_names', [])),
            "positions": self._safe_list(row.get('positions', [])),
            "start_dates": self._safe_list(start_dates_raw),
            "end_dates": self._safe_list(end_dates_raw)
        }
        
        # Calculate experience years
        experience_years = self._calculate_experience_years(
            self._safe_list(start_dates_raw),
            self._safe_list(end_dates_raw)
        )
        
        # Responsibilities
        responsibilities = self._safe_list(row.get('responsibilities', []))
        
        return {
            "skills": skills,
            "skill_count": len(skills),
            "education": education,
            "experience": experience,
            "experience_years": experience_years,
            "responsibilities": responsibilities,
            "career_objective": self._safe_str(row.get('career_objective', '')),
            "languages": self._safe_list(row.get('languages', [])),
            "certifications": self._safe_list(row.get('certification_skills', []))
        }
    
    def _calculate_experience_years(self, start_dates: List, end_dates: List) -> float:
        """Calculate total experience in years from dates."""
        if not start_dates or not end_dates:
            return 0.0
        
        total_years = 0
        current_year = 2026
        
        for start, end in zip(start_dates, end_dates):
            try:
                start_year = self._extract_year(start)
                end_year = self._extract_year(end)
                
                if start_year:
                    if end_year and end_year not in ['Till Date', 'Present', '2026']:
                        years = int(end_year) - int(start_year)
                    else:
                        years = current_year - int(start_year)
                    total_years += max(0, years)
            except Exception:
                continue
        
        return float(total_years)
    
    def _extract_year(self, date_str) -> Optional[str]:
        """Extract year from date string."""
        if date_str is None:
            return None
        
        # Convert to string safely
        date_str = str(date_str).strip()
        
        if not date_str or date_str in ['nan', 'None', '']:
            return None
        
        if 'Till Date' in date_str or 'Present' in date_str:
            return '2026'
        
        match = re.search(r'(19|20)\d{2}', date_str)
        return match.group(0) if match else None
    
    def _precompute_embeddings(self) -> Dict[int, Any]:
        """Pre-compute embeddings for all resumes with caching."""
        if self.embedding_model is None:
            return {}
        
        # Check cache first
        cached = self._load_cached_embeddings()
        if cached is not None:
            self._embeddings_cache = cached
            return cached
        
        print("⚙️ Pre-computing embeddings for all resumes (this may take 1-2 minutes)...")
        embeddings = {}
        total = len(self.df)
        
        for idx, row in self.df.iterrows():
            try:
                # Combine text for embedding
                skills = self._safe_list(row.get('skills', []))
                responsibilities = self._safe_list(row.get('responsibilities', []))
                career_objective = self._safe_str(row.get('career_objective', ''))
                
                text = " ".join(skills + responsibilities + [career_objective])
                if text.strip():
                    embedding = self.embedding_model.encode([text[:1000]])[0]
                    embeddings[int(idx)] = embedding
            except Exception as e:
                continue
            
            if (idx + 1) % 1000 == 0:
                print(f"   Processed {idx + 1}/{total} resumes")
        
        print(f"✅ Computed {len(embeddings)} embeddings")
        self._embeddings_cache = embeddings
        self._save_cached_embeddings(embeddings)
        return embeddings
    
    def calculate_match_score(self, candidate: Dict, job_requirements: Dict) -> Dict:
        """Calculate match score between candidate and job requirements."""
        scores = {}
        
        # Skill match (40%)
        skill_score = self._calculate_skill_match(
            candidate.get('skills', []),
            self._safe_list(job_requirements.get('skills_required', []))
        )
        scores['skill_match'] = skill_score * 0.4
        
        # Experience match (25%)
        exp_score = self._calculate_experience_match(
            candidate.get('experience_years', 0),
            self._safe_str(job_requirements.get('experiencere_requirement', ''))
        )
        scores['experience_match'] = exp_score * 0.25
        
        # Education match (20%)
        edu_score = self._calculate_education_match(
            candidate.get('education', {}),
            self._safe_str(job_requirements.get('educationaL_requirements', ''))
        )
        scores['education_match'] = edu_score * 0.20
        
        # Semantic similarity (15%)
        semantic_score = self._calculate_semantic_similarity(candidate, job_requirements)
        scores['semantic_match'] = semantic_score * 0.15
        
        scores['total_score'] = sum(scores.values())
        scores['score_breakdown'] = {
            'skills': scores['skill_match'] / 0.4 if scores['skill_match'] > 0 else 0,
            'experience': scores['experience_match'] / 0.25 if scores['experience_match'] > 0 else 0,
            'education': scores['education_match'] / 0.20 if scores['education_match'] > 0 else 0,
            'semantic': scores['semantic_match'] / 0.15 if scores['semantic_match'] > 0 else 0
        }
        
        # Matching and missing skills
        candidate_skills = set(str(s).lower().strip() for s in candidate.get('skills', []) if s)
        required_skills = set(str(s).lower().strip() for s in job_requirements.get('skills_required', []) if s)
        scores['matching_skills'] = list(candidate_skills & required_skills)
        scores['missing_skills'] = list(required_skills - candidate_skills)
        
        return scores
    
    def _calculate_match_score_fast(self, candidate: Dict, job_requirements: Dict, 
                                      job_embedding: Any, candidate_embedding: Any) -> Dict:
        """Fast match score calculation with cached embeddings."""
        scores = {}
        
        # Skill match (40%)
        skill_score = self._calculate_skill_match(
            candidate.get('skills', []),
            self._safe_list(job_requirements.get('skills_required', []))
        )
        scores['skill_match'] = skill_score * 0.4
        
        # Experience match (25%)
        exp_score = self._calculate_experience_match(
            candidate.get('experience_years', 0),
            self._safe_str(job_requirements.get('experiencere_requirement', ''))
        )
        scores['experience_match'] = exp_score * 0.25
        
        # Education match (20%)
        edu_score = self._calculate_education_match(
            candidate.get('education', {}),
            self._safe_str(job_requirements.get('educationaL_requirements', ''))
        )
        scores['education_match'] = edu_score * 0.20
        
        # Semantic similarity (15%) - use cached embeddings
        semantic_score = 0.5
        if job_embedding is not None and candidate_embedding is not None:
            try:
                similarity = cosine_similarity([job_embedding], [candidate_embedding])[0][0]
                semantic_score = float(similarity)
            except:
                pass
        scores['semantic_match'] = semantic_score * 0.15
        
        scores['total_score'] = sum(scores.values())
        scores['score_breakdown'] = {
            'skills': scores['skill_match'] / 0.4 if scores['skill_match'] > 0 else 0,
            'experience': scores['experience_match'] / 0.25 if scores['experience_match'] > 0 else 0,
            'education': scores['education_match'] / 0.20 if scores['education_match'] > 0 else 0,
            'semantic': scores['semantic_match'] / 0.15 if scores['semantic_match'] > 0 else 0
        }
        
        # Matching and missing skills
        candidate_skills = set(str(s).lower().strip() for s in candidate.get('skills', []) if s)
        required_skills = set(str(s).lower().strip() for s in job_requirements.get('skills_required', []) if s)
        scores['matching_skills'] = list(candidate_skills & required_skills)
        scores['missing_skills'] = list(required_skills - candidate_skills)
        
        return scores
    
    def _calculate_skill_match(self, candidate_skills: List, required_skills: List) -> float:
        if not required_skills:
            return 1.0
        if not candidate_skills:
            return 0.0
        
        candidate_set = set(str(s).lower().strip() for s in candidate_skills if s)
        required_set = set(str(s).lower().strip() for s in required_skills if s)
        
        if not required_set:
            return 1.0
        
        matches = 0
        for req in required_set:
            for cand in candidate_set:
                if req in cand or cand in req:
                    matches += 1
                    break
        
        return min(1.0, matches / len(required_set))
    
    def _calculate_experience_match(self, candidate_years: float, requirement: str) -> float:
        if not requirement:
            return 1.0
        
        match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', str(requirement).lower())
        if match:
            required_years = float(match.group(1))
            if candidate_years >= required_years:
                return 1.0
            return max(0.2, candidate_years / required_years)
        
        return 0.8
    
    def _calculate_education_match(self, candidate_education: Dict, requirement: str) -> float:
        if not requirement:
            return 1.0
        
        req_lower = requirement.lower()
        degrees = [str(d).lower() for d in candidate_education.get('degrees', []) if d]
        fields = [str(f).lower() for f in candidate_education.get('fields', []) if f]
        
        degree_keywords = ['bachelor', 'master', 'phd', 'b.s', 'm.s', 'b.sc', 'm.sc']
        for keyword in degree_keywords:
            if keyword in req_lower:
                for degree in degrees:
                    if keyword in degree:
                        return 1.0
        
        field_keywords = ['computer science', 'engineering', 'data science', 'ai', 'ml']
        for keyword in field_keywords:
            if keyword in req_lower:
                for field in fields:
                    if keyword in field:
                        return 0.8
        
        return 0.5
    
    def _calculate_semantic_similarity(self, candidate: Dict, job_requirements: Dict) -> float:
        if self.embedding_model is None:
            return 0.5
        
        candidate_text = " ".join([
            " ".join(candidate.get('skills', [])),
            " ".join(candidate.get('responsibilities', [])),
            candidate.get('career_objective', '')
        ])
        
        job_text = " ".join([
            " ".join(self._safe_list(job_requirements.get('skills_required', []))),
            self._safe_str(job_requirements.get('responsibilities.1', '')),
            self._safe_str(job_requirements.get('educationaL_requirements', ''))
        ])
        
        if not candidate_text or not job_text:
            return 0.5
        
        try:
            cand_emb = self.embedding_model.encode([candidate_text[:1000]])
            job_emb = self.embedding_model.encode([job_text[:1000]])
            similarity = cosine_similarity(cand_emb, job_emb)[0][0]
            return float(similarity)
        except:
            return 0.5
    
    def get_top_candidates_for_job(self, job_position: str, limit: int = 10) -> List[Dict]:
        """Get top candidates for a specific job position (optimized with caching)."""
        try:
            if self.df is None:
                self.load_data()
            
            job_col = self.column_mappings.get('job_position', 'job_position_name')
            
            if job_col not in self.df.columns:
                print(f"Column '{job_col}' not found!")
                return []
            
            # Find matching job
            matching_jobs = self.df[self.df[job_col].str.contains(job_position, case=False, na=False)]
            
            if len(matching_jobs) == 0:
                return []
            
            job_index = matching_jobs.index[0]
            job_row = self.df.iloc[job_index]
            
            skills_required = self._safe_list(job_row.get('skills_required', []))
            
            job_requirements = {
                'skills_required': skills_required,
                'experiencere_requirement': self._safe_str(job_row.get('experiencere_requirement', '')),
                'educationaL_requirements': self._safe_str(job_row.get('educationaL_requirements', '')),
                'responsibilities.1': self._safe_str(job_row.get('responsibilities.1', '')),
                'job_position_name': self._safe_str(job_row.get(job_col, ''))
            }
            
            # Pre-compute job embedding once
            job_text = " ".join([
                " ".join(skills_required),
                self._safe_str(job_row.get('responsibilities.1', '')),
                self._safe_str(job_row.get('educationaL_requirements', ''))
            ])
            
            job_embedding = None
            if self.embedding_model and job_text.strip():
                job_embedding = self.embedding_model.encode([job_text[:1000]])[0]
            
            # Get cached embeddings
            cached_embeddings = self._precompute_embeddings()
            
            results = []
            total = len(self.df)
            print(f"⚙️ Matching {total} candidates for '{job_position}'...")
            
            for idx, row in self.df.iterrows():
                if idx == job_index:
                    continue
                
                try:
                    candidate_features = self.extract_candidate_features(row)
                    
                    # Calculate match scores with cached embeddings
                    match_scores = self._calculate_match_score_fast(
                        candidate_features, 
                        job_requirements,
                        job_embedding,
                        cached_embeddings.get(int(idx))
                    )
                    
                    matched_score = row.get('matched_score', 0)
                    try:
                        if pd.isna(matched_score):
                            matched_score = 0
                    except:
                        pass
                    
                    results.append({
                        'candidate_index': int(idx),
                        'candidate_features': candidate_features,
                        'match_scores': match_scores,
                        'matched_score': float(matched_score) if matched_score else 0
                    })
                except Exception as e:
                    continue
                
                if (idx + 1) % 1000 == 0:
                    print(f"   Processed {idx + 1}/{total} candidates")
            
            results.sort(key=lambda x: x['match_scores']['total_score'], reverse=True)
            print(f"✅ Found {len(results)} candidates")
            return results[:limit]
        except Exception as e:
            print(f"Error in get_top_candidates_for_job: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_all_job_positions(self) -> Dict[str, int]:
        """Get all unique job positions with counts."""
        if self.df is None:
            self.load_data()
        
        job_col = self.column_mappings.get('job_position', 'job_position_name')
        if job_col in self.df.columns:
            return self.df[job_col].value_counts().to_dict()
        return {}