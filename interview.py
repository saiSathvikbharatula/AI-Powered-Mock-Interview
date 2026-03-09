# interview.py
from __future__ import annotations

import os
import json
import re
import tempfile
import streamlit as st
from groq import Groq

from audio_features import extract_audio_features
from webrtc_realtime import FaceScoreBuffer, start_realtime_capture


# ==========================================================
# GROQ SETUP
# ==========================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")

client = Groq(api_key=GROQ_API_KEY)


# ==========================================================
# JSON HELPERS
# ==========================================================
def _extract_json_array(text: str):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\[[\s\S]*\]", text)
        return json.loads(match.group(0)) if match else None


def _extract_json_object(text: str):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{[\s\S]*\}", text)
        return json.loads(match.group(0)) if match else None


# ==========================================================
# LLM QUESTION GENERATION
# ==========================================================
def generate_qa(role: str, difficulty: str, n: int = 5):
    prompt = f"""
Generate EXACTLY {n} interview questions for role: {role}
Difficulty: {difficulty}

Return ONLY JSON:
[
  {{
    "question": "...",
    "ideal_answer": "..."
  }}
]
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = resp.choices[0].message.content or ""
    arr = _extract_json_array(raw)

    if not isinstance(arr, list):
        raise ValueError("LLM did not return valid JSON array")

    return arr[:n]


# ==========================================================
# WHISPER
# ==========================================================
@st.cache_resource
def load_whisper():
    from faster_whisper import WhisperModel
    return WhisperModel("small.en", device="cpu", compute_type="int8")


def transcribe_audio(audio_bytes: bytes) -> str:
    model = load_whisper()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name

    try:
        segments, _ = model.transcribe(path, language="en")
        return " ".join(seg.text.strip() for seg in segments if seg.text.strip())
    finally:
        os.unlink(path)


# ==========================================================
# LLM CONTENT SCORING
# ==========================================================
def score_answer(question: str, ideal_answer: str, user_answer: str):
    prompt = f"""
Question:
{question}

Ideal answer:
{ideal_answer}

Candidate answer:
{user_answer}

Return ONLY JSON:
{{
  "relevance": 0-100,
  "clarity": 0-100,
  "technical_depth": 0-100,
  "content_score": 0-100,
  "one_line_feedback": "..."
}}
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = resp.choices[0].message.content or ""
    obj = _extract_json_object(raw)

    if not isinstance(obj, dict):
        raise ValueError("Invalid scoring JSON")

    def clamp(x):
        try:
            return max(0, min(100, int(round(float(x)))))
        except:
            return 0

    return {
        "relevance": clamp(obj.get("relevance", 0)),
        "clarity": clamp(obj.get("clarity", 0)),
        "technical_depth": clamp(obj.get("technical_depth", 0)),
        "content_score": clamp(obj.get("content_score", 0)),
        "one_line_feedback": str(obj.get("one_line_feedback", "")).strip(),
    }


# ==========================================================
# INTERVIEW PAGE
# ==========================================================
def interview_page():

    st.markdown("""
    <div style='text-align:center; padding-bottom:10px'>
        <h1>🎤 AI Mock Interview</h1>
        <p>Answer confidently. AI evaluates your performance.</p>
    </div>
    """, unsafe_allow_html=True)

    # -------- SESSION INIT --------
    defaults = {
        "qa_items": [],
        "current_q": 0,
        "content_scores": {},
        "visual_scores": {},
        "audio_scores": {},
        "face_buffer": FaceScoreBuffer(),
    }

    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    role = st.session_state.get("role")
    difficulty = st.session_state.get("difficulty")

    if not role or not difficulty:
        st.session_state["page"] = "setup"
        st.rerun()
        return

    # -------- GENERATE QUESTIONS --------
    if not st.session_state["qa_items"]:
        with st.spinner("Generating interview questions..."):
            st.session_state["qa_items"] = generate_qa(role, difficulty, n=5)

    qa_items = st.session_state["qa_items"]
    q_idx = st.session_state["current_q"]

    if q_idx >= len(qa_items):
        st.session_state["page"] = "results"
        st.rerun()
        return

    question = qa_items[q_idx]["question"]
    ideal_answer = qa_items[q_idx]["ideal_answer"]

    # -------- Question Card --------
    st.markdown(f"""
    <div style='background: rgba(255,255,255,0.08);
                padding:20px;
                border-radius:15px;
                margin-bottom:20px'>
        <h3>📝 Question {q_idx + 1}</h3>
        <p style='font-size:18px'>{question}</p>
    </div>
    """, unsafe_allow_html=True)

    # -------- Progress Bar --------
    progress = (q_idx + 1) / len(qa_items)
    st.progress(progress)
    st.caption(f"Progress: {q_idx + 1} of {len(qa_items)}")

    st.divider()

    # -------- Camera Section --------
    #st.markdown("### 📷 Live Confidence Analysis")
    start_realtime_capture(
        key="interview_camera",
        face_buffer=st.session_state["face_buffer"],
        playing=True,
    )

    st.divider()

    # -------- Audio Section --------
    st.markdown("### 🎙 Record Your Answer")
    audio_input = st.audio_input("Click mic → Speak → Stop", sample_rate=16000)

    manual_text = st.text_area("📝 Optional: Type your answer here")

    st.divider()

    # -------- Analyze Button --------
    if st.button("✅ Analyze & Next"):

        transcript = ""
        if audio_input:
            with st.spinner("Transcribing..."):
                transcript = transcribe_audio(audio_input.getvalue())

        final_text = transcript.strip() or manual_text.strip()

        # -------- VISUAL SCORE --------
        st.session_state["visual_scores"][q_idx] = (
            st.session_state["face_buffer"].snapshot()
        )

        # -------- AUDIO SCORE --------
        if audio_input and final_text:
            audio_feat = extract_audio_features(
                audio_input.getvalue(),
                final_text
            )
        else:
            audio_feat = {
                "audio_confidence": 0,
                "fluency_score": 0,
            }

        st.session_state["audio_scores"][q_idx] = audio_feat

        # -------- CONTENT SCORE --------
        if final_text:
            with st.spinner("Scoring answer..."):
                scores = score_answer(question, ideal_answer, final_text)
        else:
            scores = {
                "relevance": 0,
                "clarity": 0,
                "technical_depth": 0,
                "content_score": 0,
                "one_line_feedback": "No answer detected.",
            }

        st.session_state["content_scores"][q_idx] = scores

        st.session_state["current_q"] += 1
        print("\n" + "=" * 70)
        print(f"QUESTION {q_idx + 1}: {question}")
        print("FINAL ANSWER:", final_text)
        print("=" * 70)

        print("VISUAL:", st.session_state["visual_scores"][q_idx])
        print("AUDIO:", audio_feat)
        print("CONTENT:", scores)
        print("=" * 70 + "\n")

        st.rerun()
