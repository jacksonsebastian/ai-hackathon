"""Resume Upload Page — AI-Powered Parsing."""
import asyncio
import streamlit as st
from app.services.resume_parser import parse_resume
from app.ui.components.resume_card import render_resume_card


st.title("📄 Upload Candidate Resume")

uploaded_file = st.file_uploader("Choose a PDF or DOCX file", type=["pdf", "docx"])

if uploaded_file is not None:
    # Clear state if a new file is uploaded
    if "last_uploaded_file" not in st.session_state or st.session_state["last_uploaded_file"] != uploaded_file.name:
        st.session_state["last_uploaded_file"] = uploaded_file.name
        st.session_state.pop("parsed_resume", None)

    if st.button("🔍 Analyze Resume with DeepSeek-R1"):
        with st.spinner("DeepSeek-R1 is analyzing your resume..."):
            try:
                bytes_data = uploaded_file.getvalue()
                resume = asyncio.run(parse_resume(bytes_data, uploaded_file.name))
                st.session_state["parsed_resume"] = resume
                st.session_state["current_resume_id"] = resume.id
            except Exception as e:
                st.error(f"Resume parsing failed: {e}")

if "parsed_resume" in st.session_state:
    st.success("✅ Resume analyzed by DeepSeek-R1")
    render_resume_card(st.session_state["parsed_resume"])
    
    if st.button("Start Interview with this Candidate"):
        st.switch_page("ui/pages/interview.py")
