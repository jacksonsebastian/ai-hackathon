"""Main Streamlit Entry Point."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from app.ui.styles.theme import apply_custom_theme

# Apply global theme
apply_custom_theme()

# Define navigation
pages = {
    "Navigation": [
        st.Page("app/ui/pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("app/ui/pages/resume_upload.py", title="Upload Resume", icon="📄"),
        st.Page("app/ui/pages/interview.py", title="Active Interview", icon="🎙️"),
        st.Page("app/ui/pages/evaluation.py", title="Results", icon="📈"),
        st.Page("app/ui/pages/settings.py", title="Settings", icon="⚙️"),
    ]
}

pg = st.navigation(pages)
pg.run()
