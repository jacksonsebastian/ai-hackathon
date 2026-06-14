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
        
        from app.services.audio_service import get_audio_service
        audio_file = asyncio.run(get_audio_service().generate_speech(q.question_text, q.id))
        
        st.session_state.messages.append({
            "role": "agent", 
            "content": q.question_text,
            "audio_file": audio_file
        })
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
            st.switch_page("ui/pages/evaluation.py")

with col1:
    st.subheader("Interview Chat")
    render_chat_history(st.session_state.messages)
    
    st.subheader("Interview Chat")
    render_chat_history(st.session_state.messages)
    
    if not st.session_state.session_id:
        st.info("Click 'Start New Session' to begin.")
        st.stop()
        
    current_q_id = st.session_state.current_question_id
    
    # Display the current question heavily emphasized (caption)
    current_msg = st.session_state.messages[-1] if st.session_state.messages else None
    if current_msg and current_msg.get("role") == "agent":
        st.markdown("### 🎙️ AI Interviewer is asking:")
        st.info(f"**{current_msg['content']}**")
        
        # Audio autoplay logic (play once per question)
        if "played_audio" not in st.session_state:
            st.session_state.played_audio = set()
            
        if current_msg.get("audio_file"):
            should_autoplay = current_q_id not in st.session_state.played_audio
            st.audio(current_msg["audio_file"], autoplay=should_autoplay)
            st.session_state.played_audio.add(current_q_id)

    st.markdown("---")
    st.markdown("### 🗣️ 1-on-1 Interview")
    st.caption("The AI is listening. Speak naturally, and click 'Done Speaking' when finished.")
    
    from app.ui.components.av_interview import av_interview
    
    # Render the custom Streamlit AV component
    av_data = av_interview(ai_speaking=False, key=f"av_{current_q_id}")
    
    if av_data is not None and av_data.get("text"):
        with st.spinner("Transcribing your audio and evaluating..."):
            transcribed_text = av_data["text"]
            proctor_img = av_data.get("proctor_img")
            
            st.session_state.messages.append({
                "role": "user", 
                "content": transcribed_text,
                "proctor_img": proctor_img
            })
            
            resume = crud.get_resume(resume_id)
            profile = resume.get_profile_text() if resume else ""
            
            # Submit answer
            eval_res = asyncio.run(st.session_state.interview_service.submit_answer(
                st.session_state.session_id,
                current_q_id,
                transcribed_text,
                profile
            ))
            
            # Get next question
            next_q = asyncio.run(st.session_state.interview_service.get_next_question(
                st.session_state.session_id, profile
            ))
            
            # Generate AI Voice
            from app.services.audio_service import get_audio_service
            audio_file = asyncio.run(get_audio_service().generate_speech(next_q.question_text, next_q.id))
            
            st.session_state.current_question_id = next_q.id
            st.session_state.messages.append({
                "role": "agent", 
                "content": next_q.question_text,
                "audio_file": audio_file
            })
        st.rerun()
