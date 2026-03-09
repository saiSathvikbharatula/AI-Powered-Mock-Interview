# results.py
import streamlit as st
from supabase_client import supabase

# ---------------- LOAD ML MODEL ----------------
@st.cache_resource
def load_readiness_model():
    import joblib
    return joblib.load("models/readiness_rf_model.joblib")


def _avg(values):
    return round(sum(values) / len(values), 2) if values else 0.0


# ---------------- FETCH PREVIOUS SCORE ----------------
def get_previous_score(user_id, current_session_id):
    response = (
        supabase.table("interview_sessions")
        .select("id, readiness_score")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    if not response.data:
        return None

    for row in response.data:
        if row["id"] != current_session_id and row["readiness_score"] is not None:
            return row["readiness_score"]

    return None


def results_page():
    st.title("📊 Interview Results")

    visual_scores = st.session_state.get("visual_scores", {})
    content_scores = st.session_state.get("content_scores", {})
    audio_scores = st.session_state.get("audio_scores", {})
    qa_items = st.session_state.get("qa_items", [])

    # ---------------- AVERAGES ----------------
    vc = [_v.get("visual_confidence", 0.0) for _v in visual_scores.values()]
    vn = [_v.get("visual_nervousness", 0.0) for _v in visual_scores.values()]

    rel = [_c.get("relevance", 0.0) for _c in content_scores.values()]
    cla = [_c.get("clarity", 0.0) for _c in content_scores.values()]
    tech = [_c.get("technical_depth", 0.0) for _c in content_scores.values()]
    cont = [_c.get("content_score", 0.0) for _c in content_scores.values()]

    ac = [_a.get("audio_confidence", 0.0) for _a in audio_scores.values()]
    fl = [_a.get("fluency_score", 0.0) for _a in audio_scores.values()]

    st.subheader("Visual Scores (Avg)")
    c1, c2 = st.columns(2)
    c1.metric("Visual Confidence", f"{_avg(vc)}/100")
    c2.metric("Visual Nervousness", f"{_avg(vn)}/100")

    st.subheader("Content Scores (Avg)")
    c3, c4, c5, c6 = st.columns(4)
    c3.metric("Relevance", f"{_avg(rel)}/100")
    c4.metric("Clarity", f"{_avg(cla)}/100")
    c5.metric("Tech Depth", f"{_avg(tech)}/100")
    c6.metric("Content Score", f"{_avg(cont)}/100")

    st.subheader("Audio Scores (Avg)")
    c7, c8 = st.columns(2)
    c7.metric("Audio Confidence", f"{_avg(ac)}/100")
    c8.metric("Fluency Score", f"{_avg(fl)}/100")

    st.divider()

    # ---------------- PER QUESTION TABLE ----------------
    st.subheader("Per Question Scores")

    rows = []
    for i in range(len(qa_items)):
        v = visual_scores.get(i, {})
        c = content_scores.get(i, {})
        a = audio_scores.get(i, {})
        q = qa_items[i].get("question", f"Q{i+1}")

        rows.append({
            "Q#": i + 1,
            "Question": q[:80] + ("..." if len(q) > 80 else ""),
            "Visual_Confidence": v.get("visual_confidence", 0.0),
            "Visual_Nervousness": v.get("visual_nervousness", 0.0),
            "Audio_Confidence": a.get("audio_confidence", 0.0),
            "Fluency": a.get("fluency_score", 0.0),
            "Relevance": c.get("relevance", 0.0),
            "Clarity": c.get("clarity", 0.0),
            "TechDepth": c.get("technical_depth", 0.0),
            "ContentScore": c.get("content_score", 0.0),
            "Feedback": c.get("one_line_feedback", ""),
        })

    st.dataframe(rows, width="stretch")

    st.divider()

    # ==========================================================
    # 🎯 FINAL READINESS SCORE
    # ==========================================================
    n = len(content_scores)

    if n > 0:
        avg_relevance = _avg(rel)
        avg_tech = _avg(tech)
        avg_content = _avg(cont)

        avg_visual_conf = _avg(vc)
        avg_visual_nerv = _avg(vn)

        avg_audio_conf = _avg(ac)
        avg_fluency = _avg(fl)

        model = load_readiness_model()

        features = [[
            avg_relevance,
            avg_tech,
            avg_content,
            avg_visual_conf,
            avg_visual_nerv,
            avg_audio_conf,
            avg_fluency,
        ]]

        final_score = round(float(model.predict(features)[0]), 2)
    else:
        final_score = 0.0

    st.metric("🎯 Final Interview Readiness Score", f"{final_score}/100")

    # ---------------- SAVE FINAL SCORE ----------------
    if st.session_state.get("session_id") and not st.session_state.get("score_saved"):
        supabase.table("interview_sessions") \
            .update({"readiness_score": final_score}) \
            .eq("id", st.session_state["session_id"]) \
            .execute()

        st.session_state["score_saved"] = True
        st.success("Readiness score saved successfully!")

    # ==========================================================
    # 📈 TREND PERFORMANCE (NEW SECTION ADDED)
    # ==========================================================
    user_id = st.session_state.get("user_id")
    session_id = st.session_state.get("session_id")

    previous_score = get_previous_score(user_id, session_id)

    if previous_score is not None:
        st.divider()
        st.subheader("📈 Performance Trend")

        diff = final_score - previous_score

        if diff > 5:
            st.success(f"You improved by {round(diff,1)} points compared to your last attempt!")
        elif diff < -5:
            st.error(f"Your score decreased by {abs(round(diff,1))} points from your last attempt.")
        else:
            st.info("Your performance is consistent with your previous attempt.")

    else:
        st.info("This is your first recorded interview attempt.")

    # ---------------- NAVIGATION ----------------
    if st.button("Back to Welcome"):
        st.session_state["page"] = "welcome"
        st.session_state["score_saved"] = False
        st.rerun()
