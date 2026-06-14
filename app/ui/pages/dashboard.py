"""Dashboard Page."""
import streamlit as st
import pandas as pd
from app.database import crud
from app.ui.components.sidebar import render_sidebar
from app.ui.components.metrics import render_metric_card

st.set_page_config(page_title="Dashboard | AI Interviewer", layout="wide")
render_sidebar()

st.title("📊 Platform Dashboard")

stats = crud.get_dashboard_stats()

col1, col2, col3, col4 = st.columns(4)
with col1: render_metric_card("Total Resumes", str(stats["total_resumes"]))
with col2: render_metric_card("Total Sessions", str(stats["total_sessions"]))
with col3: render_metric_card("Completed", str(stats["completed_sessions"]))
with col4: render_metric_card("Avg Score", f"{stats['average_score']}/100")

st.markdown("---")
st.subheader("Recent Sessions")
sessions = crud.get_all_sessions()[:10]
if sessions:
    df = pd.DataFrame([{
        "ID": s.id[:8],
        "Type": s.session_type,
        "Status": s.status,
        "Round": s.current_round,
        "Started": s.created_at
    } for s in sessions])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No interview sessions found.")
