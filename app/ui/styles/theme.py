"""
Custom Streamlit theme and CSS styling.
"""

import streamlit as st

def apply_custom_theme():
    """Inject custom CSS for modern UI design."""
    st.markdown("""
        <style>
        /* Glassmorphism effects */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Metric cards */
        div[data-testid="metric-container"] {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 5% 5% 5% 10%;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Chat bubbles */
        .user-bubble {
            background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
            color: white;
            border-radius: 15px 15px 0 15px;
            padding: 10px 15px;
            margin: 10px 0;
            max-width: 80%;
            float: right;
            clear: both;
        }
        
        .agent-bubble {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 15px 15px 15px 0;
            padding: 10px 15px;
            margin: 10px 0;
            max-width: 80%;
            float: left;
            clear: both;
        }
        </style>
    """, unsafe_allow_html=True)
