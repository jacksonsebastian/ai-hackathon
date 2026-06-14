"""UI Sidebar Component."""
import streamlit as st
from app.config import settings

def render_sidebar():
    with st.sidebar:
        st.title("🤖 AI Interviewer")
        st.markdown("---")
        
        st.page_link("app/main.py", label="Dashboard", icon="📊")
        st.page_link("app/ui/pages/resume_upload.py", label="Upload Resume", icon="📄")
        st.page_link("app/ui/pages/interview.py", label="Active Interview", icon="🎙️")
        st.page_link("app/ui/pages/evaluation.py", label="Results & Reports", icon="📈")
        st.page_link("app/ui/pages/settings.py", label="Settings", icon="⚙️")
        
        st.markdown("---")
        st.caption(f"Environment: {settings.ENVIRONMENT.upper()}")
        st.caption(f"Provider: {settings.MODEL_PROVIDER.upper()}")
