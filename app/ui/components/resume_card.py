"""UI Resume Card Component."""
import streamlit as st
from app.database.models import Resume

def render_resume_card(resume: Resume):
    """Render resume details."""
    with st.expander(f"📄 Candidate Profile: {resume.candidate_name}", expanded=True):
        st.markdown(f"**Email:** {resume.email} | **Phone:** {resume.phone}")
        if resume.skills:
            st.markdown(f"**Top Skills:** {', '.join(resume.skills[:10])}")
        if resume.summary:
            st.markdown(f"**Summary:** {resume.summary}")
