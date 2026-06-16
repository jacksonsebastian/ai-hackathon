"""Main Streamlit Entry Point."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="AI Interviewer", layout="wide", page_icon="🤖")

from app.ui.styles.theme import apply_custom_theme
from app.config import settings

# Apply global theme
apply_custom_theme()

# Sidebar environment info
with st.sidebar:
    st.caption(f"🔧 Environment: {settings.ENVIRONMENT.upper()}")
    st.caption(f"🤖 Model: {settings.vllm.model_name.split('/')[-1]}")

# Define navigation (single source of truth — no render_sidebar() in pages)
pages = {
    "Navigation": [
        st.Page("ui/pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("ui/pages/resume_upload.py", title="Upload Resume", icon="📄"),
        st.Page("ui/pages/interview.py", title="Active Interview", icon="🎙️"),
        st.Page("ui/pages/coding.py", title="Coding Assessment", icon="💻"),
        st.Page("ui/pages/evaluation.py", title="Results & Reports", icon="📈"),
        st.Page("ui/pages/settings.py", title="Settings", icon="⚙️"),
    ]
}

pg = st.navigation(pages)
pg.run()
