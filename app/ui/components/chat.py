"""UI Chat Component."""
import streamlit as st

def render_chat_history(messages):
    """Render chat history with custom styling."""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "user":
            st.markdown(f'<div class="user-bubble"><b>You</b><br/>{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="agent-bubble"><b>{role.title()}</b><br/>{content}</div>', unsafe_allow_html=True)
            
    # Clear floats
    st.markdown('<div style="clear: both;"></div>', unsafe_allow_html=True)
