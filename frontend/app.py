"""
Main Streamlit frontend for Resume Screener.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.config import *
from frontend.utils import *

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #6C63FF;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #2D3436;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #6C63FF 0%, #4A3FCF 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .skill-tag {
        background: #F0F0F0;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        display: inline-block;
        margin: 0.2rem;
        font-size: 0.85rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        height: 100%;
    }
    .success-badge {
        background: #00B894;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
    .warning-badge {
        background: #FDCB6E;
        color: #2D3436;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
    .danger-badge {
        background: #E17055;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_position' not in st.session_state:
    st.session_state.selected_position = None
if 'candidates' not in st.session_state:
    st.session_state.candidates = None
if 'job_analysis' not in st.session_state:
    st.session_state.job_analysis = None
if 'uploaded_text' not in st.session_state:
    st.session_state.uploaded_text = None


def show_sidebar():
    """Show the sidebar with navigation."""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/resume.png", width=80)
        st.markdown(f"## {APP_ICON} {APP_TITLE}")
        st.markdown("---")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "🎯 Match Candidates", "📄 Upload Resume", "📊 Analytics"],
            index=0
        )
        
        st.markdown("---")
        
        # API Status
        st.markdown("### 🔌 API Status")
        health = safe_request(ENDPOINTS["health"])
        if health and health.get("status") == "healthy":
            st.success("✅ Connected")
            st.caption(f"Environment: {health.get('environment', 'N/A')}")
        else:
            st.error("❌ Disconnected")
            st.caption("Make sure the API server is running")
        
        st.markdown("---")
        st.caption(f"Version 1.0.0 | {datetime.now().strftime('%Y-%m-%d')}")
        
        return page


def show_dashboard():
    """Show the dashboard page."""
    st.markdown('<div class="main-header">📊 Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Overview of your resume screening system</div>', unsafe_allow_html=True)
    
    # Get dataset info
    dataset_info = safe_request(ENDPOINTS["dataset_info"])
    
    if dataset_info:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📄 Total Resumes",
                dataset_info.get("total_resumes", 0),
                help="Total resumes in the database"
            )
        
        with col2:
            st.metric(
                "💼 Job Positions",
                dataset_info.get("sample_job_positions", {}).__len__(),
                help="Unique job positions available"
            )
        
        with col3:
            st.metric(
                "🛠️ Skills Extracted",
                dataset_info.get("has_skills", 0),
                help="Resumes with extracted skills"
            )
        
        with col4:
            st.metric(
                "🎓 Education Records",
                dataset_info.get("has_education", 0),
                help="Resumes with education data"
            )
        
        # Job positions distribution
        st.markdown("### 📊 Job Positions Distribution")
        
        positions = dataset_info.get("sample_job_positions", {})
        if positions:
            df_positions = pd.DataFrame({
                'Position': list(positions.keys()),
                'Count': list(positions.values())
            })
            
            fig = go.Figure(data=[
                go.Bar(
                    x=df_positions['Position'],
                    y=df_positions['Count'],
                    marker_color='#6C63FF',
                    text=df_positions['Count'],
                    textposition='outside',
                )
            ])
            fig.update_layout(
                title="Top Job Positions",
                xaxis_title="Position",
                yaxis_title="Number of Resumes",
                height=400,
                showlegend=False,
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Could not load dataset information. Make sure the API is running.")


def show_match_candidates():
    """Show the match candidates page."""
    st.markdown('<div class="main-header">🎯 Match Candidates</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Find the best candidates for any job position</div>', unsafe_allow_html=True)
    
    # Get job positions
    positions_data = safe_request(ENDPOINTS["job_positions"])
    
    if positions_data:
        positions = list(positions_data.get("positions", {}).keys())
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            job_position = st.selectbox(
                "Select Job Position",
                positions,
                index=positions.index(st.session_state.selected_position) if st.session_state.selected_position in positions else 0
            )
        
        with col2:
            limit = st.number_input(
                "Number of Candidates",
                min_value=1,
                max_value=50,
                value=10,
                step=1
            )
        
        # Search button
        if st.button("🔍 Find Candidates", type="primary", use_container_width=True):
            with st.spinner(f"Searching for candidates for '{job_position}'..."):
                response = safe_request(
                    ENDPOINTS["match_candidates"],
                    method="POST",
                    params={"job_position": job_position, "limit": limit}
                )
                
                if response:
                    st.session_state.candidates = response
                    st.session_state.selected_position = job_position
                    st.success(f"✅ Found {response.get('total_candidates_matched', 0)} candidates")
        
        # Display candidates
        if st.session_state.candidates:
            candidates = st.session_state.candidates.get("top_candidates", [])
            
            if candidates:
                st.markdown(f"### Top {len(candidates)} Candidates for '{st.session_state.selected_position}'")
                
                for i, candidate in enumerate(candidates):
                    with st.expander(f"#{i+1} - Score: {format_score(candidate['total_score'])} - {get_score_label(candidate['total_score'])}", expanded=i==0):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.markdown(f"**Candidate ID:** {candidate['candidate_index']}")
                            st.markdown(f"**Experience:** {format_experience(candidate['experience_years'])}")
                            st.markdown(f"**Dataset Score:** {format_score(candidate.get('dataset_match_score', 0))}")
                        
                        with col2:
                            st.markdown("**Score Breakdown:**")
                            st.markdown(f"🛠️ Skills: {format_score(candidate['score_breakdown']['skills'])}")
                            st.markdown(f"💼 Experience: {format_score(candidate['score_breakdown']['experience'])}")
                            st.markdown(f"🎓 Education: {format_score(candidate['score_breakdown']['education'])}")
                            st.markdown(f"🧠 Semantic: {format_score(candidate['score_breakdown']['semantic'])}")
                        
                        with col3:
                            if candidate.get('matching_skills'):
                                st.markdown("**✅ Matching Skills:**")
                                for skill in candidate['matching_skills'][:5]:
                                    st.markdown(f"<span class='skill-tag'>✅ {skill}</span>", unsafe_allow_html=True)
                            
                            if candidate.get('missing_skills'):
                                st.markdown("**❌ Missing Skills:**")
                                for skill in candidate['missing_skills'][:5]:
                                    st.markdown(f"<span class='skill-tag'>❌ {skill}</span>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown(f"**Skills:** {', '.join(candidate.get('skills', [])[:10])}")
                        if candidate.get('top_education'):
                            st.markdown(f"**Education:** {', '.join(candidate.get('top_education', []))}")
    else:
        st.warning("Could not load job positions. Make sure the API is running.")


def show_upload_resume():
    """Show the upload resume page."""
    st.markdown('<div class="main-header">📄 Upload Resume</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a resume to extract and analyze its content</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a resume file (PDF format)",
        type=['pdf'],
        help="Upload a PDF resume to extract text and analyze skills"
    )
    
    if uploaded_file is not None:
        # Save uploaded file
        files = {'file': ('resume.pdf', uploaded_file.getvalue(), 'application/pdf')}
        
        with st.spinner("Processing resume..."):
            response = safe_request(
                ENDPOINTS["upload_pdf"],
                method="POST",
                files=files
            )
            
            if response:
                st.session_state.uploaded_text = response
                
                # Display results
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("📄 Pages", response.get('page_count', 0))
                
                with col2:
                    st.metric("📝 Characters", response.get('text_length', 0))
                
                with col3:
                    st.metric("🔧 Method", response.get('extraction_method', 'N/A'))
                
                st.markdown("### 📝 Extracted Text")
                
                # Show first 500 characters
                text = response.get('text', '')
                st.text_area(
                    "Text Preview",
                    text[:1000] + ("..." if len(text) > 1000 else ""),
                    height=200,
                    disabled=True
                )
                
                # Extract skills from text
                st.markdown("### 🛠️ Detected Skills")
                skills = extract_skills_from_text(text)
                if skills:
                    cols = st.columns(5)
                    for i, skill in enumerate(skills):
                        with cols[i % 5]:
                            st.markdown(f"<span class='skill-tag'>✅ {skill}</span>", unsafe_allow_html=True)
                else:
                    st.info("No skills detected. Try uploading a resume with clearer skill sections.")
                
                # Metadata
                with st.expander("📋 Metadata"):
                    metadata = response.get('metadata', {})
                    for key, value in metadata.items():
                        st.text(f"{key}: {value}")


def show_analytics():
    """Show the analytics page."""
    st.markdown('<div class="main-header">📊 Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Visualize your resume screening data</div>', unsafe_allow_html=True)
    
    dataset_info = safe_request(ENDPOINTS["dataset_info"])
    
    if dataset_info:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Data Overview")
            
            metrics = {
                "Total Resumes": dataset_info.get("total_resumes", 0),
                "Unique Positions": len(dataset_info.get("sample_job_positions", {})),
                "Has Skills": dataset_info.get("has_skills", 0),
                "Has Education": dataset_info.get("has_education", 0),
                "Has Experience": dataset_info.get("has_experience", 0),
            }
            
            # Create a gauge chart for data completeness
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=dataset_info.get("has_skills", 0) / dataset_info.get("total_resumes", 1) * 100,
                title={'text': "Data Completeness"},
                delta={'reference': 80},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#6C63FF"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"},
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Position Distribution")
            positions = dataset_info.get("sample_job_positions", {})
            if positions:
                df = pd.DataFrame({
                    'Position': list(positions.keys()),
                    'Count': list(positions.values())
                })
                
                fig = go.Figure(data=[
                    go.Pie(
                        labels=df['Position'],
                        values=df['Count'],
                        hole=0.3,
                        marker_colors=['#6C63FF', '#00B894', '#FDCB6E', '#E17055', '#0984E3']
                    )
                ])
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # Additional stats
        st.markdown("### 📋 Summary Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### ✅ Data Quality")
            st.progress(dataset_info.get("has_skills", 0) / dataset_info.get("total_resumes", 1))
            st.caption(f"Skills Coverage: {dataset_info.get('has_skills', 0) / dataset_info.get('total_resumes', 1) * 100:.1f}%")
        
        with col2:
            st.markdown("#### 🎯 Skills per Resume")
            avg_skills = dataset_info.get("has_skills", 0) / dataset_info.get("total_resumes", 1)
            st.metric("Average Skills", f"{avg_skills:.1f}")
        
        with col3:
            st.markdown("#### 🏆 Top Position")
            if positions:
                top_pos = max(positions, key=positions.get)
                st.metric("Most Common", top_pos, f"{positions[top_pos]} resumes")
    else:
        st.warning("Could not load analytics data. Make sure the API is running.")


def main():
    """Main application entry point."""
    page = show_sidebar()
    
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🎯 Match Candidates":
        show_match_candidates()
    elif page == "📄 Upload Resume":
        show_upload_resume()
    elif page == "📊 Analytics":
        show_analytics()


if __name__ == "__main__":
    main()