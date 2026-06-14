"""Main Streamlit Entry Point."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="AI Interviewer", layout="wide")

from app.ui.styles.theme import apply_custom_theme

# Apply global theme
apply_custom_theme()

# Define navigation
pages = {
    "Navigation": [
        st.Page("ui/pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("ui/pages/resume_upload.py", title="Upload Resume", icon="📄"),
        st.Page("ui/pages/interview.py", title="Active Interview", icon="🎙️"),
        st.Page("ui/pages/evaluation.py", title="Results", icon="📈"),
        st.Page("ui/pages/settings.py", title="Settings", icon="⚙️"),
    ]
}

pg = st.navigation(pages)
pg.run()
