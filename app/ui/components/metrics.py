"""UI Metrics Component."""
import streamlit as st

def render_metric_card(title: str, value: str, delta: str = None):
    """Render a styled metric card."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.metric(label=title, value=value, delta=delta)
    st.markdown('</div>', unsafe_allow_html=True)
