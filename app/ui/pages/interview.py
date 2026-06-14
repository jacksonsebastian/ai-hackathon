"""Active Interview Page."""
import asyncio
import streamlit as st
from app.database import crud
from app.services.interview_service import InterviewService
from app.ui.components.sidebar import render_sidebar
from app.ui.components.chat import render_chat_history


render_sidebar()

st.title("🎙️ Active Interview Session")

if "interview_service" not in st.session_state:
    st.session_state.interview_service = InterviewService()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = None

resume_id = st.session_state.get("current_resume_id")

if not resume_id:
    st.warning("Please upload and select a candidate resume first.")
    st.stop()

col1, col2 = st.columns([3, 1])

with col2:
    st.subheader("Controls")
    if st.button("Start New Session"):
        session = st.session_state.interview_service.start_session(resume_id)
        st.session_state.session_id = session.id
        st.session_state.messages = [{"role": "system", "content": "Interview session started."}]
        resume = crud.get_resume(resume_id)
        q = asyncio.run(st.session_state.interview_service.get_next_question(
            session.id, resume.get_profile_text() if resume else ""
        ))
        st.session_state.current_question_id = q.id
        st.session_state.messages.append({"role": "agent", "content": q.question_text})
        st.rerun()
        
    if st.button("End Interview & Generate Report"):
        if st.session_state.session_id:
            with st.spinner("Generating comprehensive report..."):
                resume = crud.get_resume(resume_id)
                asyncio.run(st.session_state.interview_service.end_session(
                    st.session_state.session_id, 
                    resume.get_profile_text() if resume else ""
                ))
            st.success("Report generated!")
            st.switch_page("app/ui/pages/evaluation.py")

with col1:
    st.subheader("Interview Chat")
    render_chat_history(st.session_state.messages)
    
    if prompt := st.chat_input("Type your answer here..."):
        if not st.session_state.session_id:
            st.error("Please start a session first.")
            st.stop()
            
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Agent is evaluating and thinking..."):
            resume = crud.get_resume(resume_id)
            profile = resume.get_profile_text() if resume else ""
            
            eval_res = asyncio.run(st.session_state.interview_service.submit_answer(
                st.session_state.session_id,
                st.session_state.current_question_id,
                prompt,
                profile
            ))
            
            next_q = asyncio.run(st.session_state.interview_service.get_next_question(
                st.session_state.session_id, profile
            ))
            st.session_state.current_question_id = next_q.id
            
            st.session_state.messages.append({"role": "agent", "content": next_q.question_text})
        st.rerun()
