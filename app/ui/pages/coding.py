"""Coding Assessment Page."""
import asyncio
import time
import streamlit as st
from app.database import crud
from app.services.interview_service import InterviewService
from app.ui.components.code_editor import render_code_editor
from app.utils.state_machine import sync_st_state, update_interview_state

st.title("💻 Coding Assessment")

state = sync_st_state()

# Navigation Guards
if state.get("current_stage") == "completed":
    st.info("Interview already completed.")
    if st.button("View Results", type="primary"):
        st.session_state.redirect_to = "ui/pages/evaluation.py"
        st.rerun()
    st.stop()
    
if not state.get("behavioral_completed") and not state.get("technical_completed"):
    st.warning("You must complete the technical and behavioral rounds first.")
    if st.button("Return to Interview"):
        st.session_state.redirect_to = "ui/pages/interview.py"
        st.rerun()
    st.stop()

session_id = st.session_state.get("session_id")
resume_id = st.session_state.get("current_resume_id")

if not session_id or not resume_id:
    st.warning("No active session found.")
    st.stop()

if "coding_problem" not in st.session_state:
    st.session_state.coding_problem = None
if "coding_feedback" not in st.session_state:
    st.session_state.coding_feedback = None

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Problem Statement")
    if st.session_state.coding_problem is None:
        with st.spinner("Generating personalized coding problem with DeepSeek-R1..."):
            service = st.session_state.get("interview_service", InterviewService())
            conductor = service.get_conductor(session_id)
            resume = crud.get_resume(resume_id)
            
            # Use real coding agent
            problem = asyncio.run(conductor.coding.generate_problem(
                resume.get_profile_text() if resume else "", "medium", "Algorithms"
            ))
            st.session_state.coding_problem = problem
            st.rerun()
            
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
    
    submit_col, skip_col = st.columns(2)
    
    with submit_col:
        submit_clicked = st.button("Submit Code", type="primary", use_container_width=True)
    with skip_col:
        skip_clicked = st.button("Skip Coding", use_container_width=True)
        
    if (submit_clicked or skip_clicked) and st.session_state.coding_problem:
        with st.spinner("DeepSeek-R1 evaluating code & finalizing interview..."):
            service = st.session_state.get("interview_service", InterviewService())
            conductor = service.get_conductor(session_id)
            
            if skip_clicked:
                code_to_eval = "def solution():\n    pass # Skipped"
            else:
                code_to_eval = code
                
            eval_res = asyncio.run(conductor.coding.evaluate_code(
                str(st.session_state.coding_problem), code_to_eval, "python"
            ))
            st.session_state.coding_feedback = eval_res
            
            # Save evaluation as part of session
            # Since it's a coding round, we add it to conductor's evaluations manually
            # or the conductor evaluates it
            resume = crud.get_resume(resume_id)
            profile = resume.get_profile_text() if resume else ""
            
            # To ensure it gets logged properly in DB
            q_text = st.session_state.coding_problem.get("question", "Coding Problem")
            
            # Using submit_answer allows the evaluator to score it fully and records the answer
            asyncio.run(service.submit_answer(
                session_id,
                "coding_question_id", # Not ideal, but conductor expects an ID. It generates one usually.
                code_to_eval,
                profile
            ))
            
            # End session
            asyncio.run(service.end_session(session_id, profile))
            
            update_interview_state(session_id, {
                "current_stage": "completed",
                "coding_completed": True,
                "evaluation_completed": True
            })
            
            st.success("Coding assessment complete. Generating final report...")
            time.sleep(2)
            st.session_state.redirect_to = "ui/pages/evaluation.py"
            st.rerun()
