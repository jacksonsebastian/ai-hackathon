"""Settings Page."""
import streamlit as st
from app.config import settings
import os


st.title("⚙️ System Settings")

st.header("Environment Configuration")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Active Provider")
    st.info(f"**Model:** {settings.vllm.model_name}")
    st.info(f"**Environment:** {settings.ENVIRONMENT.upper()}")
    
    vllm_url = st.text_input("vLLM Base URL", value=settings.vllm.base_url)
    vllm_model = st.text_input("vLLM Model Name", value=settings.vllm.model_name)

with col2:
    st.subheader("Model Status")
    # Check vLLM health
    import httpx
    try:
        resp = httpx.get(f"{settings.vllm.base_url.rstrip('/v1')}/v1/models", timeout=5)
        if resp.status_code == 200:
            st.success("🟢 DeepSeek-R1 (vLLM): Connected")
        else:
            st.error("🔴 DeepSeek-R1 (vLLM): Error")
    except Exception:
        st.warning("🟡 DeepSeek-R1 (vLLM): Not reachable")
    
    # Whisper & Kokoro status
    from app.services.audio_service import get_audio_service
    audio_status = get_audio_service().get_model_status()
    if audio_status["whisper"] == "loaded":
        st.success("🟢 Whisper Large V3: Loaded")
    else:
        st.info("🟡 Whisper Large V3: Will load on first use")
    if audio_status["kokoro"] == "loaded":
        st.success("🟢 Kokoro TTS: Loaded")
    else:
        st.info("🟡 Kokoro TTS: Will load on first use")

st.markdown("---")
st.header("Interview Configuration")
max_q = st.slider("Max Questions per Interview", 5, 30, settings.agent.max_total_questions)
adaptive = st.checkbox("Enable Adaptive Difficulty", value=settings.agent.enable_adaptive_difficulty)

st.markdown("---")
st.header("Timer Configuration")
enable_timer = st.checkbox("Enable Question Timer", value=True)
timer_type = st.radio("Timer Type", ["Per Question", "Entire Interview"], horizontal=True)
if timer_type == "Per Question":
    timer_duration = st.slider("Seconds per Question", 30, 300, 120)
else:
    timer_duration = st.slider("Minutes for Entire Interview", 5, 60, 30)

st.markdown("---")
st.header("Question Distribution")
tech_q = st.slider("Technical Questions", 1, 15, settings.agent.technical_question_count)
behav_q = st.slider("Behavioral Questions", 1, 10, settings.agent.behavioral_question_count)
code_q = st.slider("Coding Questions", 0, 5, settings.agent.coding_question_count)

st.markdown("---")
st.header("Video Proctoring & Integrity")
enable_video = st.checkbox("Enable Video Monitoring", value=settings.video_monitoring.enabled)
enable_ai_video = st.checkbox("Enable AI Integrity Analysis", value=settings.video_monitoring.enable_ai_analysis, disabled=not enable_video)
video_interval = st.selectbox("Snapshot Capture Interval", [10, 15, 30, 60, 120], index=[10, 15, 30, 60, 120].index(settings.video_monitoring.capture_interval_seconds) if settings.video_monitoring.capture_interval_seconds in [10, 15, 30, 60, 120] else 2, format_func=lambda x: f"Every {x} seconds", disabled=not enable_video)

if st.button("Save Configuration", type="primary"):
    import dotenv
    env_path = os.path.join(os.getcwd(), ".env")
    
    # Save to .env file
    dotenv.set_key(env_path, "VLLM_BASE_URL", vllm_url)
    dotenv.set_key(env_path, "VLLM_MODEL", vllm_model)
    dotenv.set_key(env_path, "MAX_TOTAL_QUESTIONS", str(max_q))
    dotenv.set_key(env_path, "TECHNICAL_QUESTION_COUNT", str(tech_q))
    dotenv.set_key(env_path, "BEHAVIORAL_QUESTION_COUNT", str(behav_q))
    dotenv.set_key(env_path, "CODING_QUESTION_COUNT", str(code_q))
    dotenv.set_key(env_path, "ENABLE_ADAPTIVE_DIFFICULTY", str(adaptive).lower())
    dotenv.set_key(env_path, "VIDEO_MONITORING_ENABLED", str(enable_video).lower())
    dotenv.set_key(env_path, "VIDEO_AI_ANALYSIS_ENABLED", str(enable_ai_video).lower())
    dotenv.set_key(env_path, "VIDEO_CAPTURE_INTERVAL", str(video_interval))
    
    # Update active settings in memory
    settings.vllm.base_url = vllm_url
    settings.vllm.model_name = vllm_model
    settings.agent.max_total_questions = max_q
    settings.agent.enable_adaptive_difficulty = adaptive
    settings.agent.technical_question_count = tech_q
    settings.agent.behavioral_question_count = behav_q
    settings.agent.coding_question_count = code_q
    
    settings.video_monitoring.enabled = enable_video
    settings.video_monitoring.enable_ai_analysis = enable_ai_video
    settings.video_monitoring.capture_interval_seconds = video_interval
    
    # Store timer config in session state
    st.session_state["timer_enabled"] = enable_timer
    st.session_state["timer_type"] = timer_type
    st.session_state["timer_limit"] = timer_duration if timer_type == "Per Question" else timer_duration * 60
    
    # Reset provider cache
    from app.services.ai_service import reset_provider
    reset_provider()
    
    st.success("Settings saved successfully!")
    st.rerun()
