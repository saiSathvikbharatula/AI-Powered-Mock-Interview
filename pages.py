import streamlit as st
from supabase_client import supabase


def welcome_page():

    st.markdown("""
    <div style='text-align:center; padding-bottom:20px'>
        <h1>🚀 Welcome to Your AI Interview Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ### 📌 What is this platform?

    AI Mock Interview is an intelligent interview practice system that evaluates:

    - 🎯 Your technical content quality
    - 🎙 Your voice confidence & fluency
    - 👁 Your visual confidence & body language
    - 📊 Your overall interview readiness score

    ---
    """)

    st.markdown("""
    ### 🧭 How to Perform the Interview

    1️⃣ Select your job role and difficulty level  
    2️⃣ Answer each question clearly and confidently  
    3️⃣ Speak naturally — AI will analyze voice & facial cues  
    4️⃣ Click **Analyze & Next** after each answer  
    5️⃣ Review your final performance report  

    ---
    """)

    st.markdown("""
    ### 💡 Tips for Best Results

    - Maintain steady eye contact  
    - Speak clearly at a moderate pace  
    - Structure your answers logically  
    - Avoid long pauses  

    ---
    """)

    if st.button("🚀 Start Mock Interview"):
        st.session_state["page"] = "setup"
        st.rerun()



def interview_setup_page():
    st.title("Interview Setup")

    role = st.text_input("Enter Job Role", placeholder="e.g., Software Engineer")
    difficulty = st.radio("Select Difficulty Level", ["Easy", "Intermediate", "Hard"])

    if st.button("🚀 Start Interview"):
        if not role.strip():
            st.warning("Please enter a job role")
            return

        st.session_state["role"] = role
        st.session_state["difficulty"] = difficulty

        response = supabase.table("interview_sessions").insert({
            "user_id": st.session_state["user_id"],
            "role": role,
            "difficulty": difficulty
        }).execute()

        st.session_state["session_id"] = response.data[0]["id"]

        # CAMERA STARTS HERE
        st.session_state["camera_active"] = True
        st.session_state["page"] = "interview"
        st.rerun()
