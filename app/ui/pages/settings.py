"""Settings Page."""
import streamlit as st
from app.config import settings
import os


from app.ui.components.sidebar import render_sidebar
render_sidebar()

st.title("⚙️ System Settings")

st.header("Environment Configuration")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Active Provider")
    provider_mode = st.radio(
        "Select Inference Mode",
        ["mock", "vllm", "openai"],
        index=["mock", "vllm", "openai"].index(settings.MODEL_PROVIDER) if settings.MODEL_PROVIDER in ["mock", "vllm", "openai"] else 0,
        help="Mock: Local Dev (No GPU) | vLLM: Jupyter GPU Environment | OpenAI: Remote API"
    )
    
    if provider_mode != settings.MODEL_PROVIDER:
        st.warning(f"You changed the provider to {provider_mode}. Click Save Configuration to apply.")

with col2:
    st.subheader("GPU Inference (vLLM)")
    vllm_url = st.text_input("vLLM Base URL", value=settings.vllm.base_url)
    vllm_model = st.text_input("vLLM Model Name", value=settings.vllm.model_name)
    
st.markdown("---")
st.header("Interview Configuration")
max_q = st.slider("Max Questions per Interview", 5, 30, settings.agent.max_total_questions)
adaptive = st.checkbox("Enable Adaptive Difficulty", value=settings.agent.enable_adaptive_difficulty)

if st.button("Save Configuration"):
    import dotenv
    env_path = os.path.join(os.getcwd(), ".env")
    
    # Save to .env file permanently
    dotenv.set_key(env_path, "MODEL_PROVIDER", provider_mode)
    dotenv.set_key(env_path, "VLLM_BASE_URL", vllm_url)
    dotenv.set_key(env_path, "VLLM_MODEL", vllm_model)
    
    # Update active settings in memory
    settings.MODEL_PROVIDER = provider_mode
    settings.vllm.base_url = vllm_url
    settings.vllm.model_name = vllm_model
    settings.agent.max_total_questions = max_q
    settings.agent.enable_adaptive_difficulty = adaptive
    
    # Clear AI Service Provider cache so it initializes the new provider
    from app.services.ai_service import reset_provider
    reset_provider()
    
    st.success("Settings saved to .env successfully! Rerunning app...")
    st.rerun()
