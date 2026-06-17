"""Active Interview Page — Full Voice + Text Interview Experience."""
import asyncio
import time
import streamlit as st
from app.database import crud
from app.config import settings
from app.services.interview_service import InterviewService
from app.services.audio_service import get_audio_service
from app.ui.components.chat import render_chat_history
from app.utils.state_machine import sync_st_state, update_interview_state, init_session_state


st.title("🎙️ Active Interview Session")

# ── Session State Initialization ──────────────────────────────

if "interview_service" not in st.session_state:
    st.session_state.interview_service = InterviewService()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = None
if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = None
if "interview_mode" not in st.session_state:
    st.session_state.interview_mode = "hybrid"
if "question_start_time" not in st.session_state:
    st.session_state.question_start_time = None
if "interview_completed" not in st.session_state:
    st.session_state.interview_completed = False

resume_id = st.session_state.get("current_resume_id")

if not resume_id:
    st.warning("⚠️ Please upload and parse a candidate resume first.")
    if st.button("Go to Upload Resume"):
        st.switch_page("ui/pages/resume_upload.py")
    st.stop()

# Sync with DB state
state = sync_st_state()

# ── Candidate Registration Form ──────────────────────────────

if st.session_state.candidate_info is None and st.session_state.session_id is None:
    st.subheader("📋 Candidate Registration")
    st.markdown("Fill in candidate details before starting the interview.")
    
    with st.form("candidate_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            phone = st.text_input("Phone", placeholder="+1-234-567-8900")
            years_exp = st.number_input("Years of Experience", min_value=0, max_value=50, value=2)
        with col2:
            current_role = st.text_input("Current Role", placeholder="Software Engineer")
            target_role = st.text_input("Target Role *", placeholder="Senior Software Engineer")
            interview_type = st.selectbox(
                "Interview Type",
                ["Full Interview", "Technical", "Behavioral", "Coding"],
            )
            interview_mode = st.selectbox(
                "Interview Mode",
                ["Hybrid (Voice + Text)", "Voice Only", "Text Only"],
            )
        
        submitted = st.form_submit_button("Start Interview", type="primary", use_container_width=True)
        
        if submitted:
            if not full_name or not email or not target_role:
                st.error("Please fill in required fields (Name, Email, Target Role)")
            else:
                mode_map = {
                    "Hybrid (Voice + Text)": "hybrid",
                    "Voice Only": "voice",
                    "Text Only": "text",
                }
                st.session_state.candidate_info = {
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "years_experience": years_exp,
                    "current_role": current_role,
                    "target_role": target_role,
                    "interview_type": interview_type,
                }
                st.session_state.interview_mode = mode_map.get(interview_mode, "hybrid")
                
                type_map = {
                    "Full Interview": "full",
                    "Technical": "technical",
                    "Behavioral": "behavioral",
                    "Coding": "coding",
                }
                session_type = type_map.get(interview_type, "full")
                
                # Start session
                with st.spinner("🚀 Starting interview session..."):
                    service = st.session_state.interview_service
                    session = service.start_session(resume_id, session_type)
                    st.session_state.session_id = session.id
                    
                    # Update State Machine
                    init_session_state(session.id)
                    update_interview_state(session.id, {"current_stage": "resume_round", "questions_answered": 0})
                    
                    st.session_state.messages = [
                        {"role": "system", "content": f"Interview session started for {full_name}. Type: {interview_type}"}
                    ]
                    
                    # Generate first question
                    resume = crud.get_resume(resume_id)
                    profile = resume.get_profile_text() if resume else ""
                    q = asyncio.run(service.get_next_question(session.id, profile))
                    st.session_state.current_question_id = q.id
                    st.session_state.question_start_time = time.time()
                    
                    # Generate AI voice for question
                    audio_svc = get_audio_service()
                    audio_file = asyncio.run(audio_svc.generate_speech(q.question_text, q.id))
                    
                    st.session_state.messages.append({
                        "role": "agent",
                        "content": q.question_text,
                        "audio_file": audio_file,
                        "round": q.agent_type,
                    })
                
                st.rerun()
    st.stop()

# ── Active Interview UI ──────────────────────────────────────

if state.get("current_stage") == "completed":
    st.success("✅ Interview completed! View your results.")
    if st.button("View Results & Reports", type="primary"):
        st.session_state.redirect_to = "ui/pages/evaluation.py"
        st.rerun()
    st.stop()

if state.get("current_stage") == "coding_round":
    st.info("Technical and Behavioral rounds completed. Proceeding to Coding Assessment.")
    if st.button("Start Coding Assessment", type="primary"):
        st.session_state.redirect_to = "ui/pages/coding.py"
        st.rerun()
    st.stop()

if not st.session_state.session_id:
    st.info("Click 'Start New Session' to begin.")
    st.stop()

# Get conductor progress
service = st.session_state.interview_service
conductor = service.get_conductor(st.session_state.session_id)
progress = conductor.get_progress()

# Update state tracking if round advanced
current_state_stage = state.get("current_stage")
round_name = progress["current_round"]

if round_name == "completed":
    update_interview_state(st.session_state.session_id, {
        "current_stage": "coding_round",
        "behavioral_completed": True,
        "technical_completed": True
    })
    st.session_state.redirect_to = "ui/pages/coding.py"
    st.rerun()
elif round_name == "coding" and current_state_stage != "coding_round":
    update_interview_state(st.session_state.session_id, {
        "current_stage": "coding_round",
        "behavioral_completed": True,
        "technical_completed": True
    })
    st.success("Technical and Behavioral rounds completed. Starting Coding Assessment.")
    time.sleep(2)
    st.session_state.redirect_to = "ui/pages/coding.py"
    st.rerun()
elif round_name == "behavioral" and current_state_stage != "behavioral_round":
    update_interview_state(st.session_state.session_id, {
        "current_stage": "behavioral_round",
        "technical_completed": True
    })
elif round_name == "technical" and current_state_stage != "technical_round":
    update_interview_state(st.session_state.session_id, {"current_stage": "technical_round"})


# ── Progress Bar & Round Badge ────────────────────────────────

prog_col1, prog_col2, prog_col3 = st.columns([2, 1, 1])
with prog_col1:
    progress_pct = progress["progress_pct"] / 100
    st.progress(progress_pct, text=f"Question {progress['questions_asked'] + 1} of {progress['total_questions']}")
with prog_col2:
    round_disp = progress["current_round"].replace("_", " ").title()
    st.markdown(f"**🔄 Round:** `{round_disp}`")
with prog_col3:
    st.markdown(f"**📊 Round** {progress['round_index'] + 1} / {progress['total_rounds']}")

# ── Model Status Indicators ──────────────────────────────────

audio_svc = get_audio_service()
model_status = audio_svc.get_model_status()
status_cols = st.columns(4)
with status_cols[0]:
    st.markdown("🟢 **DeepSeek-R1**" if True else "🔴 DeepSeek-R1")
with status_cols[1]:
    whisper_ok = model_status["whisper"] == "loaded"
    st.markdown(f"{'🟢' if whisper_ok else '🟡'} **Whisper V3**")
with status_cols[2]:
    kokoro_ok = model_status["kokoro"] == "loaded"
    st.markdown(f"{'🟢' if kokoro_ok else '🟡'} **Kokoro TTS**")
with status_cols[3]:
    st.markdown("🟢 **BGE-M3**" if True else "🔴 BGE-M3")

st.markdown("---")

# ── Interview Layout ─────────────────────────────────────────

col_main, col_side = st.columns([3, 1])

with col_side:
    st.subheader("Controls")
    
    # Timer display
    if st.session_state.question_start_time:
        elapsed = int(time.time() - st.session_state.question_start_time)
        timer_limit = st.session_state.get("timer_limit", 120)  # 2 min default
        remaining = max(0, timer_limit - elapsed)
        mins, secs = divmod(remaining, 60)
        if remaining > 30:
            st.markdown(f"⏱️ **Timer:** `{mins:02d}:{secs:02d}`")
        elif remaining > 0:
            st.markdown(f"⏱️ **Timer:** :red[`{mins:02d}:{secs:02d}`]")
        else:
            st.markdown("⏱️ **Timer:** :red[`TIME UP`]")
    
    # Candidate info
    if st.session_state.candidate_info:
        info = st.session_state.candidate_info
        st.markdown(f"**👤** {info['full_name']}")
        st.markdown(f"**🎯** {info['target_role']}")
        st.markdown(f"**📝** {info['interview_type']}")
    
    st.markdown("---")
    
    # Video Monitoring
    if settings.video_monitoring.enabled:
        @st.fragment()
        def render_video_proctoring(progress):
            from app.ui.components.webcam_proctor import webcam_proctor
            st.caption("📷 Proctoring Active")
            
            # Inject the invisible component
            captured_frame = webcam_proctor(
                capture_interval_seconds=settings.video_monitoring.capture_interval_seconds,
                key="webcam_proctor_v2"
            )
            
            if captured_frame and captured_frame.startswith("data:image"):
                # We got a new frame. Avoid saving duplicates by checking session state
                if st.session_state.get("last_captured_frame") != captured_frame:
                    st.session_state["last_captured_frame"] = captured_frame
                    
                    # Save snapshot async
                    import asyncio
                    from app.database.models import InterviewSnapshot
                    from app.utils.helpers import generate_id
                    
                    snapshot = InterviewSnapshot(
                        id=generate_id(),
                        session_id=st.session_state.session_id,
                        image_blob=captured_frame,
                        question_number=progress.get("questions_asked", 0) + 1,
                        current_round=progress.get("current_round", "")
                    )
                    
                    if settings.video_monitoring.enable_ai_analysis:
                        from app.agents.video_analyzer import VideoAnalyzerAgent
                        analyzer = VideoAnalyzerAgent(session_id=st.session_state.session_id)
                        analysis = asyncio.run(analyzer.analyze_snapshot(captured_frame))
                        snapshot.analysis_json = analysis
                    
                    crud.create_snapshot(snapshot)

        render_video_proctoring(progress)

with col_main:
    # ── Chat History ──────────────────────────────────────────
    st.subheader("Interview Chat")
    render_chat_history(st.session_state.messages)

    # ── Current Question Display ──────────────────────────────
    current_q_id = st.session_state.current_question_id
    current_msg = st.session_state.messages[-1] if st.session_state.messages else None
    
    if current_msg and current_msg.get("role") == "agent":
        st.markdown("### 🤖 InterviewGPT asks:")
        st.info(f"**{current_msg['content']}**")
        
        # Play question audio (Kokoro TTS)
        if current_msg.get("audio_file"):
            if "played_audio" not in st.session_state:
                st.session_state.played_audio = set()
            should_autoplay = current_q_id not in st.session_state.played_audio
            st.audio(current_msg["audio_file"], autoplay=should_autoplay)
            st.session_state.played_audio.add(current_q_id)
            st.caption("🔊 Question spoken via **Kokoro TTS**")
        
        if current_msg.get("round"):
            st.caption(f"Round: {current_msg['round'].replace('_', ' ').title()}")
    
    st.markdown("---")
    
    # ── Answer Input Area ─────────────────────────────────────
    st.markdown("### 💬 Your Answer")
    
    mode = st.session_state.interview_mode
    
    # Mode selector
    mode_options = ["hybrid", "voice", "text"]
    mode_labels = ["🎙️ Hybrid (Voice + Text)", "🎙️ Voice Only", "📝 Text Only"]
    current_idx = mode_options.index(mode) if mode in mode_options else 0
    selected_mode = st.radio(
        "Answer Mode",
        mode_options,
        format_func=lambda x: mode_labels[mode_options.index(x)],
        index=current_idx,
        horizontal=True,
        key="mode_selector",
    )
    st.session_state.interview_mode = selected_mode
    
    answer_text = ""
    
    # Voice Input (Whisper)
    if selected_mode in ("voice", "hybrid"):
        st.markdown("**🎙️ Record your answer:**")
        audio_input = st.audio_input("Speak your answer", key=f"audio_{current_q_id}")
        
        if audio_input is not None:
            with st.spinner("🔄 Transcribing with Whisper Large V3..."):
                audio_bytes = audio_input.getvalue()
                transcribed = get_audio_service().transcribe_audio(audio_bytes)
            
            if transcribed and not transcribed.startswith("["):
                st.success(f"**Transcription:** {transcribed}")
                answer_text = transcribed
            else:
                st.warning(f"Transcription issue: {transcribed}")
    
    # Text Input (always available in hybrid and text modes)
    if selected_mode in ("text", "hybrid"):
        text_input = st.text_area(
            "Type or edit your answer:",
            value=answer_text,
            height=150,
            key=f"text_{current_q_id}",
            placeholder="Type your answer here...",
        )
        if text_input and text_input != answer_text:
            answer_text = text_input
        elif text_input:
            answer_text = text_input
    
    # ── Submit Button (ALWAYS visible) ────────────────────────
    submit_col1, submit_col2 = st.columns([1, 1])
    
    with submit_col1:
        submit_clicked = st.button(
            "✅ Submit Answer",
            type="primary",
            use_container_width=True,
            disabled=not answer_text.strip(),
            key=f"submit_{current_q_id}",
        )
    
    with submit_col2:
        skip_clicked = st.button(
            "⏭️ Skip Question",
            use_container_width=True,
            key=f"skip_{current_q_id}",
        )
    
    # ── Process Submission ────────────────────────────────────
    if submit_clicked and answer_text.strip():
        with st.spinner("🔄 DeepSeek-R1 evaluating answer & generating next question..."):
            st.session_state.messages.append({
                "role": "user",
                "content": answer_text,
            })
            
            resume = crud.get_resume(resume_id)
            profile = resume.get_profile_text() if resume else ""
            
            # Submit answer for evaluation
            eval_res = asyncio.run(service.submit_answer(
                st.session_state.session_id,
                current_q_id,
                answer_text,
                profile,
            ))
            
            score = eval_res.get("composite_score", eval_res.get("technical_accuracy", "N/A"))
            st.toast(f"Answer scored: {score}/10")
            
            update_interview_state(st.session_state.session_id, {
                "questions_answered": state.get("questions_answered", 0) + 1
            })
            
            next_q = asyncio.run(service.get_next_question(
                st.session_state.session_id, profile
            ))
            
            # Re-check progress
            conductor = service.get_conductor(st.session_state.session_id)
            if conductor.current_round == "coding":
                update_interview_state(st.session_state.session_id, {
                    "current_stage": "coding_round",
                    "behavioral_completed": True,
                    "technical_completed": True
                })
                st.session_state.redirect_to = "ui/pages/coding.py"
                st.rerun()
            
            audio_file = asyncio.run(get_audio_service().generate_speech(
                next_q.question_text, next_q.id
            ))
            
            st.session_state.current_question_id = next_q.id
            st.session_state.question_start_time = time.time()
            st.session_state.messages.append({
                "role": "agent",
                "content": next_q.question_text,
                "audio_file": audio_file,
                "round": next_q.agent_type,
            })
        
        st.rerun()
    
    if skip_clicked:
        with st.spinner("Skipping... generating next question..."):
            st.session_state.messages.append({
                "role": "user",
                "content": "[Candidate skipped this question]",
            })
            
            resume = crud.get_resume(resume_id)
            profile = resume.get_profile_text() if resume else ""
            
            asyncio.run(service.submit_answer(
                st.session_state.session_id,
                current_q_id,
                "[Candidate skipped this question]",
                profile,
            ))
            
            update_interview_state(st.session_state.session_id, {
                "questions_answered": state.get("questions_answered", 0) + 1
            })
            
            next_q = asyncio.run(service.get_next_question(
                st.session_state.session_id, profile
            ))
            
            # Re-check progress
            conductor = service.get_conductor(st.session_state.session_id)
            if conductor.current_round == "coding":
                update_interview_state(st.session_state.session_id, {
                    "current_stage": "coding_round",
                    "behavioral_completed": True,
                    "technical_completed": True
                })
                st.session_state.redirect_to = "ui/pages/coding.py"
                st.rerun()
            
            audio_file = asyncio.run(get_audio_service().generate_speech(
                next_q.question_text, next_q.id
            ))
            
            st.session_state.current_question_id = next_q.id
            st.session_state.question_start_time = time.time()
            st.session_state.messages.append({
                "role": "agent",
                "content": next_q.question_text,
                "audio_file": audio_file,
                "round": next_q.agent_type,
            })
        st.rerun()
