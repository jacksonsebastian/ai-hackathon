"""Evaluation Results Page — HR-Friendly Report with Scores."""
import streamlit as st
import pandas as pd
import plotly.express as px
from app.database import crud
from app.utils.state_machine import sync_st_state

st.title("📈 Interview Evaluation Report")

state = sync_st_state()

sessions = crud.get_all_sessions()
completed_sessions = [s for s in sessions if s.status == "completed"]

if not completed_sessions:
    if state.get("current_stage") != "completed" and state.get("current_stage") != "resume_uploaded":
        st.info("Your interview is currently in progress. Complete it to view the results.")
        if st.button("Return to Interview"):
            if state.get("current_stage") == "coding_round":
                st.session_state.redirect_to = "ui/pages/coding.py"
                st.rerun()
            else:
                st.session_state.redirect_to = "ui/pages/interview.py"
                st.rerun()
        st.stop()
    else:
        st.info("No completed interview sessions found. Please complete an interview first.")
        st.stop()

session_opts = {f"{s.id[:8]} - {s.created_at[:16]}": s.id for s in completed_sessions}

# Select box for session
selected_opt = st.selectbox("Select an Interview Session", list(session_opts.keys()), index=0)
session_id = session_opts[selected_opt]

report = crud.get_feedback_report(session_id)
evaluations = crud.get_evaluations_for_session(session_id)
questions = crud.get_questions_for_session(session_id)
answers = crud.get_answers_for_session(session_id)
session = crud.get_session(session_id)

if not report:
    st.warning("Report is still generating or not found for this session. It may take a minute after completion.")
    st.stop()

# ── PASS/FAIL Banner ──────────────────────────────────────────

if report.hiring_recommendation.upper() == "PASS":
    st.success("## ✅ FINAL DECISION: PASS")
else:
    st.error("## ❌ FINAL DECISION: FAIL")

# ── Candidate Info ────────────────────────────────────────────

if session and session.resume_id:
    resume = crud.get_resume(session.resume_id)
    if resume:
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.markdown(f"**👤 Candidate:** {resume.candidate_name}")
            st.markdown(f"**📧 Email:** {resume.email}")
        with info_col2:
            st.markdown(f"**📱 Phone:** {resume.phone}")
            st.markdown(f"**📄 Resume:** {resume.filename}")
        with info_col3:
            st.markdown(f"**📅 Date:** {session.created_at[:16] if session.created_at else 'N/A'}")
            st.markdown(f"**📋 Type:** {session.session_type}")

st.markdown("---")

# ── Score Overview ────────────────────────────────────────────

st.subheader("📊 Performance Metrics")

score_col1, score_col2, score_col3, score_col4 = st.columns(4)

with score_col1:
    st.metric("Overall Score", f"{report.overall_score}/100")
with score_col2:
    st.metric("Technical Score", f"{report.technical_score}/100")
with score_col3:
    st.metric("Behavioral Score", f"{report.behavioral_score}/100")
with score_col4:
    st.metric("Coding Score", f"{report.coding_score}/100")

# ── Summary & Strengths/Weaknesses ───────────────────────────

st.markdown("---")

st.subheader("📝 Executive Summary")
st.write(report.summary)

col_s, col_w = st.columns(2)

with col_s:
    st.subheader("💪 Key Strengths")
    if report.strengths:
        for strength in report.strengths:
            st.markdown(f"- {strength}")
    else:
        st.write("No specific strengths noted.")

with col_w:
    st.subheader("🎯 Areas for Improvement")
    if report.weaknesses:
        for weakness in report.weaknesses:
            st.markdown(f"- {weakness}")
    else:
        st.write("No specific weaknesses noted.")

# ── Interview Integrity Report ───────────────────────────────

st.markdown("---")
st.subheader("🛡️ Interview Integrity Report")

snapshots = crud.get_snapshots_for_session(session_id)

if not snapshots:
    st.info("No video proctoring data available for this session.")
else:
    # Calculate integrity score and risk level based on AI analysis
    analyzed_snapshots = [s for s in snapshots if s.analysis_json]
    
    if analyzed_snapshots:
        high_risk_count = 0
        medium_risk_count = 0
        
        for s in analyzed_snapshots:
            obs = s.analysis_json
            # Simple heuristic for risk calculation
            if obs.get("multiple_people_detected") or obs.get("phone_detected") or obs.get("additional_screen_detected"):
                high_risk_count += 1
            elif obs.get("is_looking_away") or obs.get("engagement_level") == "low" or not obs.get("candidate_visible"):
                medium_risk_count += 1
                
        # Base score 100
        integrity_score = 100 - (high_risk_count * 15) - (medium_risk_count * 5)
        integrity_score = max(0, integrity_score)
        
        if integrity_score >= 90:
            risk_level = "🟢 LOW RISK"
        elif integrity_score >= 70:
            risk_level = "🟡 MEDIUM RISK"
        else:
            risk_level = "🔴 HIGH RISK"
            
        int_col1, int_col2 = st.columns(2)
        with int_col1:
            st.metric("Integrity Score", f"{integrity_score}/100")
        with int_col2:
            st.markdown(f"**Risk Level:** {risk_level}")
            
        st.caption(f"Based on {len(analyzed_snapshots)} analyzed snapshots out of {len(snapshots)} total.")
        
    else:
        st.info(f"{len(snapshots)} snapshots captured. AI Analysis was disabled or unavailable.")

    # Render Evidence Gallery Timeline
    with st.expander("📸 View Evidence Gallery & Timeline"):
        st.write("Automatically captured webcam snapshots from the interview.")
        
        # Display in a grid of 3 columns
        cols = st.columns(3)
        for i, s in enumerate(snapshots):
            with cols[i % 3]:
                # Streamlit displays base64 natively if passed as markdown image or st.image using raw bytes
                # But st.image accepts base64 data URIs in newer Streamlit versions, or we can just parse it
                import base64
                from io import BytesIO
                from PIL import Image
                
                try:
                    # Parse data URI: data:image/jpeg;base64,.....
                    if "," in s.image_blob:
                        header, base64_data = s.image_blob.split(",", 1)
                        image_bytes = base64.b64decode(base64_data)
                        img = Image.open(BytesIO(image_bytes))
                        st.image(img, use_column_width=True)
                    else:
                        st.error("Invalid image format.")
                except Exception as e:
                    st.error("Error loading snapshot.")
                
                st.caption(f"**Time:** {s.captured_at[11:19]} | **Round:** {s.current_round.replace('_', ' ').title()} Q{s.question_number}")
                
                if s.analysis_json:
                    obs = s.analysis_json
                    flags = []
                    if obs.get("multiple_people_detected"): flags.append("Multiple People")
                    if obs.get("phone_detected"): flags.append("Phone Detected")
                    if not obs.get("candidate_visible"): flags.append("Candidate Not Visible")
                    if obs.get("is_looking_away"): flags.append("Looking Away")
                    
                    if flags:
                        st.markdown(f"⚠️ :red[{', '.join(flags)}]")
                    else:
                        st.markdown("✅ No unusual activity")

# ── Full Q&A Transcript (Hidden by default) ──────────────────

st.markdown("---")

with st.expander("🔍 Show Detailed Interview Transcript"):
    # Build answer lookup by question_id
    answer_map = {a.question_id: a for a in answers}
    eval_map = {e.question_id: e for e in evaluations}

    if questions:
        for i, q in enumerate(questions, 1):
            answer = answer_map.get(q.id)
            evaluation = eval_map.get(q.id)
            
            score_text = f" — Score: {evaluation.composite_score}/10" if evaluation else ""
            with st.expander(f"Q{i} [{q.agent_type.title()}]{score_text}"):
                st.markdown(f"**🤖 Question:** {q.question_text}")
                st.markdown(f"**Category:** {q.category} | **Difficulty:** {q.difficulty}")
                
                if answer:
                    st.markdown(f"**💬 Answer:** {answer.answer_text}")
                else:
                    st.markdown("**💬 Answer:** *No answer recorded*")
                
                if evaluation:
                    eval_cols = st.columns(4)
                    with eval_cols[0]:
                        st.metric("Technical", f"{evaluation.technical_accuracy}/10")
                    with eval_cols[1]:
                        st.metric("Depth", f"{evaluation.depth_of_understanding}/10")
                    with eval_cols[2]:
                        st.metric("Clarity", f"{evaluation.communication_clarity}/10")
                    with eval_cols[3]:
                        st.metric("Problem Solving", f"{evaluation.problem_solving}/10")
                    
                    st.markdown(f"**Reasoning:** {evaluation.reasoning}")
                    if evaluation.key_strengths:
                        st.markdown(f"**Strengths:** {', '.join(evaluation.key_strengths)}")
                    if evaluation.areas_to_improve:
                        st.markdown(f"**To Improve:** {', '.join(evaluation.areas_to_improve)}")
    else:
        st.info("No questions found for this session.")

    # ── Per-Question Breakdown (legacy) ───────────────────────────
    st.subheader("📊 Score Distribution")
    if evaluations:
        eval_df = pd.DataFrame([{
            "Question": f"Q{i+1}",
            "Score": ev.composite_score,
            "Type": ev.question_id[:8],
        } for i, ev in enumerate(evaluations)])
        fig2 = px.line(eval_df, x="Question", y="Score", markers=True, range_y=[0, 10])
        fig2.update_layout(title="Score Progression Across Questions")
        st.plotly_chart(fig2, use_container_width=True)
