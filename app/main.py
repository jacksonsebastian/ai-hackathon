"""Main Streamlit Entry Point."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(page_title="InterviewGPT", layout="wide", page_icon="🤖")

from app.ui.styles.theme import apply_custom_theme
from app.config import settings
from app.utils.state_machine import sync_st_state

# Apply global theme
apply_custom_theme()

# Sidebar environment info
with st.sidebar:
    st.caption(f"🔧 Environment: {settings.ENVIRONMENT.upper()}")
    st.caption(f"🤖 Model: {settings.vllm.model_name.split('/')[-1]}")

# Sync state
state = sync_st_state()
has_active_interview = st.session_state.get("session_id") is not None
is_completed = state.get("current_stage") == "completed"
can_code = state.get("technical_completed", False) and state.get("behavioral_completed", False)
can_view_results = state.get("evaluation_completed", False)

# Define navigation dynamically based on state
nav_items = [
    st.Page("ui/pages/dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("ui/pages/resume_upload.py", title="Upload Resume", icon="📄"),
    st.Page("ui/pages/interview.py", title="Active Interview", icon="🎙️"),
]

if can_code and not is_completed:
    nav_items.append(st.Page("ui/pages/coding.py", title="Coding Assessment", icon="💻"))

if can_view_results or is_completed:
    nav_items.append(st.Page("ui/pages/evaluation.py", title="Results & Reports", icon="📈"))

nav_items.append(st.Page("ui/pages/settings.py", title="Settings", icon="⚙️"))

pages = {"Navigation": nav_items}
pg = st.navigation(pages)

# Workaround for Streamlit switch_page API exceptions with dynamic navigation
if "redirect_to" in st.session_state and st.session_state.redirect_to:
    target = st.session_state.redirect_to
    st.session_state.redirect_to = None
    st.switch_page(target)

pg.run()

