"""Resume Upload Page."""
import asyncio
import streamlit as st
from app.services.resume_parser import parse_resume, parse_resume_basic
from app.ui.components.sidebar import render_sidebar
from app.ui.components.resume_card import render_resume_card

st.set_page_config(page_title="Upload Resume", layout="wide")
render_sidebar()

st.title("📄 Upload Candidate Resume")

uploaded_file = st.file_uploader("Choose a PDF or DOCX file", type=["pdf", "docx"])
use_llm = st.checkbox("Enable Deep LLM Parsing (Slower but more accurate)", value=True)

if uploaded_file is not None:
    if st.button("Parse Resume"):
        with st.spinner("Parsing resume..."):
            bytes_data = uploaded_file.getvalue()
            if use_llm:
                resume = asyncio.run(parse_resume(bytes_data, uploaded_file.name))
            else:
                resume = parse_resume_basic(bytes_data, uploaded_file.name)
            
            st.success("Resume parsed successfully!")
            st.session_state["current_resume_id"] = resume.id
            render_resume_card(resume)
            
            if st.button("Start Interview with this Candidate"):
                st.switch_page("app/ui/pages/interview.py")
