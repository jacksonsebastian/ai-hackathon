"""Evaluation Results Page."""
import streamlit as st
import pandas as pd
import plotly.express as px
from app.database import crud
from app.ui.components.sidebar import render_sidebar
from app.evaluation.report import generate_markdown_report

st.set_page_config(page_title="Evaluation Results", layout="wide")
render_sidebar()

st.title("📈 Interview Evaluation & Reports")

sessions = crud.get_all_sessions()
completed_sessions = [s for s in sessions if s.status == "completed"]

if not completed_sessions:
    st.info("No completed interview sessions found. Please complete an interview first.")
    st.stop()

session_opts = {f"{s.id[:8]} - {s.created_at[:16]}": s.id for s in completed_sessions}
selected_opt = st.selectbox("Select an Interview Session", list(session_opts.keys()))
session_id = session_opts[selected_opt]

report = crud.get_feedback_report(session_id)
evaluations = crud.get_evaluations_for_session(session_id)

if not report:
    st.warning("Report is still generating or not found for this session.")
    st.stop()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Score Overview")
    df = pd.DataFrame({
        "Category": ["Overall", "Technical", "Behavioral", "Coding"],
        "Score": [report.overall_score, report.technical_score, report.behavioral_score, report.coding_score]
    })
    fig = px.bar(df, x="Category", y="Score", text="Score", color="Category", range_y=[0, 100])
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Evaluation Details")
    st.markdown(generate_markdown_report({
        "hiring_recommendation": report.hiring_recommendation,
        "overall_score": report.overall_score,
        "technical_score": report.technical_score,
        "behavioral_score": report.behavioral_score,
        "coding_score": report.coding_score,
        "summary": report.summary,
        "strengths": report.strengths,
        "weaknesses": report.weaknesses,
        "detailed_feedback": report.detailed_feedback
    }))

st.markdown("---")
st.subheader("Per-Question Breakdown")
if evaluations:
    for ev in evaluations:
        with st.expander(f"Question Evaluation (Score: {ev.composite_score}/10)"):
            st.markdown(f"**Technical:** {ev.technical_accuracy} | **Depth:** {ev.depth_of_understanding} | **Clarity:** {ev.communication_clarity} | **Problem Solving:** {ev.problem_solving}")
            st.markdown(f"**Reasoning:** {ev.reasoning}")
            if ev.key_strengths:
                st.markdown(f"**Strengths:** {', '.join(ev.key_strengths)}")
            if ev.areas_to_improve:
                st.markdown(f"**To Improve:** {', '.join(ev.areas_to_improve)}")
