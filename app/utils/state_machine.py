"""
Interview State Machine Manager.

Handles strict interview state tracking, storing the state in the session config
to persist across page reloads and enforcing linear progression.
"""

from typing import Dict, Any
import streamlit as st
from app.database import crud
from app.database.models import InterviewSession

DEFAULT_STATE = {
    "current_stage": "resume_uploaded",  # resume_uploaded, candidate_registered, resume_round, technical_round, behavioral_round, coding_round, evaluation, completed
    "current_question": None,
    "questions_answered": 0,
    "questions_remaining": 0,
    "technical_completed": False,
    "behavioral_completed": False,
    "coding_completed": False,
    "evaluation_completed": False,
    "report_generated": False,
}

def get_interview_state(session_id: str) -> Dict[str, Any]:
    """Retrieve the current state from the database."""
    session = crud.get_session(session_id)
    if not session:
        return DEFAULT_STATE.copy()
    
    state = session.config.get("interview_state", DEFAULT_STATE.copy())
    
    # Ensure all default keys exist
    for k, v in DEFAULT_STATE.items():
        if k not in state:
            state[k] = v
            
    return state

def update_interview_state(session_id: str, updates: Dict[str, Any]) -> None:
    """Update specific fields in the interview state and persist to DB."""
    session = crud.get_session(session_id)
    if not session:
        return
        
    state = get_interview_state(session_id)
    state.update(updates)
    
    # Update config in DB
    session.config["interview_state"] = state
    crud.update_session_status(session_id, status=session.status, config=session.to_db_row()["config"])
    
    # Also update Streamlit session state if it matches the current session
    if st.session_state.get("session_id") == session_id:
        st.session_state["interview_state"] = state

def init_session_state(session_id: str) -> None:
    """Initialize state for a new session."""
    update_interview_state(session_id, {
        "current_stage": "candidate_registered"
    })

def sync_st_state() -> Dict[str, Any]:
    """Sync Streamlit session state with DB state for the current session."""
    session_id = st.session_state.get("session_id")
    if session_id:
        state = get_interview_state(session_id)
        st.session_state["interview_state"] = state
        return state
    return DEFAULT_STATE.copy()
