"""Resume Upload Page."""
import asyncio
import streamlit as st
from app.services.resume_parser import parse_resume, parse_resume_basic
from app.ui.components.resume_card import render_resume_card


st.title("📄 Upload Candidate Resume")

uploaded_file = st.file_uploader("Choose a PDF or DOCX file", type=["pdf", "docx"])
use_llm = st.checkbox("Enable Deep LLM Parsing (DeepSeek-R1)", value=True)

if uploaded_file is not None:
    # Clear state if a new file is uploaded
    if "last_uploaded_file" not in st.session_state or st.session_state["last_uploaded_file"] != uploaded_file.name:
        st.session_state["last_uploaded_file"] = uploaded_file.name
        st.session_state.pop("parsed_resume", None)

    if st.button("Parse Resume"):
        with st.spinner("Parsing resume with DeepSeek-R1..."):
            bytes_data = uploaded_file.getvalue()
            if use_llm:
                resume = asyncio.run(parse_resume(bytes_data, uploaded_file.name))
            else:
                resume = parse_resume_basic(bytes_data, uploaded_file.name)
            
            st.session_state["parsed_resume"] = resume
            st.session_state["current_resume_id"] = resume.id

if "parsed_resume" in st.session_state:
    st.success("Resume parsed successfully!")
    render_resume_card(st.session_state["parsed_resume"])
    
    if st.button("Start Interview with this Candidate"):
        st.switch_page("ui/pages/interview.py")
