"""UI Resume Card Component."""
import streamlit as st
from app.database.models import Resume

def render_resume_card(resume: Resume):
    """Render detailed resume profile."""
    with st.expander(f"📄 Candidate Profile: {resume.candidate_name}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**👤 Name:** {resume.candidate_name}")
            st.markdown(f"**📧 Email:** {resume.email or 'N/A'}")
            st.markdown(f"**📱 Phone:** {resume.phone or 'N/A'}")
        with col2:
            st.markdown(f"**📄 File:** {resume.filename}")
            st.markdown(f"**📁 Type:** {resume.file_type.upper()}")
        
        if resume.skills:
            st.markdown(f"**🛠️ Skills:** {', '.join(resume.skills[:15])}")
        
        if resume.technologies:
            st.markdown(f"**💻 Technologies:** {', '.join(resume.technologies[:10])}")
        
        if resume.experience:
            st.markdown("**💼 Experience:**")
            for exp in resume.experience[:3]:
                title = exp.get("title", "N/A")
                company = exp.get("company", "N/A")
                duration = exp.get("duration", "")
                st.markdown(f"  - {title} at {company} ({duration})")
        
        if resume.education:
            st.markdown("**🎓 Education:**")
            for edu in resume.education[:3]:
                degree = edu.get("degree", "N/A")
                institution = edu.get("institution", "N/A")
                st.markdown(f"  - {degree} — {institution}")
        
        if resume.projects:
            st.markdown("**🚀 Projects:**")
            for proj in resume.projects[:3]:
                name = proj.get("name", "N/A")
                desc = proj.get("description", "")
                st.markdown(f"  - **{name}**: {desc[:100]}")
        
        if resume.summary:
            st.markdown(f"**📝 Summary:** {resume.summary}")
        
        if resume.strengths:
            st.markdown(f"**✅ Strengths:** {', '.join(resume.strengths[:5])}")
        
        if resume.gaps:
            st.markdown(f"**⚠️ Gaps:** {', '.join(resume.gaps[:5])}")
