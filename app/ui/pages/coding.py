"""Coding Assessment Page."""
import asyncio
import streamlit as st
from app.database import crud
from app.services.interview_service import InterviewService
from app.ui.components.sidebar import render_sidebar
from app.ui.components.code_editor import render_code_editor

st.set_page_config(page_title="Coding Assessment", layout="wide")
render_sidebar()

st.title("💻 Coding Assessment")

if "coding_problem" not in st.session_state:
    st.session_state.coding_problem = None
if "coding_feedback" not in st.session_state:
    st.session_state.coding_feedback = None

resume_id = st.session_state.get("current_resume_id")
if not resume_id:
    st.warning("Please upload a resume first.")
    st.stop()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Problem Statement")
    if st.button("Generate Problem"):
        with st.spinner("Generating personalized coding problem..."):
            service = InterviewService()
            conductor = service.get_conductor("temp_coding_session")
            resume = crud.get_resume(resume_id)
            problem = asyncio.run(conductor.coding.generate_problem(
                resume.get_profile_text() if resume else "", "medium", "Algorithms"
            ))
            st.session_state.coding_problem = problem
    
    if st.session_state.coding_problem:
        prob = st.session_state.coding_problem
        st.markdown(f"**{prob.get('question', 'Problem')}**")
        st.markdown("**Examples:**")
        for ex in prob.get("examples", []):
            st.code(f"Input: {ex.get('input')}\nOutput: {ex.get('output')}\nExplanation: {ex.get('explanation')}")
        st.markdown(f"**Constraints:** {', '.join(prob.get('constraints', []))}")

with col2:
    st.subheader("Code Editor")
    code = render_code_editor("# Write your python solution here\n\ndef solution():\n    pass")
    
    if st.button("Submit Code") and st.session_state.coding_problem:
        with st.spinner("Evaluating code..."):
            service = InterviewService()
            conductor = service.get_conductor("temp_coding_session")
            eval_res = asyncio.run(conductor.coding.evaluate_code(
                str(st.session_state.coding_problem), code, "python"
            ))
            st.session_state.coding_feedback = eval_res
            
    if st.session_state.coding_feedback:
        st.subheader("Evaluation Results")
        fb = st.session_state.coding_feedback
        st.metric("Correctness", f"{fb.get('correctness', 0)}/10")
        st.metric("Efficiency", f"{fb.get('efficiency', 0)}/10")
        st.markdown(f"**Time Complexity:** {fb.get('time_complexity', 'N/A')}")
        st.markdown(f"**Space Complexity:** {fb.get('space_complexity', 'N/A')}")
        st.info(fb.get("feedback", ""))
