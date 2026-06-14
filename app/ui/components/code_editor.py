"""UI Code Editor Component."""
import streamlit as st

def render_code_editor(default_code: str = "", language: str = "python") -> str:
    """Render a simple code editor area."""
    return st.text_area("Code Editor", value=default_code, height=300, key="code_input")
