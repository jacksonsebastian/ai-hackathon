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
        st.warning(f"You changed the provider to {provider_mode}. In a real app, this would write to .env and reload.")

with col2:
    st.subheader("GPU Inference (vLLM)")
    vllm_url = st.text_input("vLLM Base URL", value=settings.vllm.base_url)
    vllm_model = st.text_input("vLLM Model Name", value=settings.vllm.model_name)
    
st.markdown("---")
st.header("Interview Configuration")
st.slider("Max Questions per Interview", 5, 30, settings.agent.max_total_questions)
st.checkbox("Enable Adaptive Difficulty", value=settings.agent.enable_adaptive_difficulty)

if st.button("Save Configuration"):
    st.success("Settings saved successfully! (In memory for this session)")
