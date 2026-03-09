import streamlit as st

from supabase_client import supabase
from auth import login_page, signup_page
from pages import welcome_page, interview_setup_page
from interview import interview_page
from streamlit.components.v1 import html
from results import results_page


# --------------------------------------------------
# MUST BE FIRST STREAMLIT COMMAND
# --------------------------------------------------
st.set_page_config(
    page_title="AI Mock Interview",
    layout="centered"
)


# --------------------------------------------------
# GLOBAL UI STYLING
# --------------------------------------------------
st.markdown("""
<style>

/* ===== APP BACKGROUND ===== */
.stApp {
    background: linear-gradient(135deg, #141e30, #243b55);
}

/* ===== FORCE TEXT WHITE ===== */
html, body, [class*="css"] {
    color: white !important;
}

/* ===== REMOVE FADED MARKDOWN EFFECT ===== */
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li {
    color: white !important;
    opacity: 1 !important;
}

/* ===== HEADINGS ===== */
h1, h2, h3, h4, h5, h6 {
    color: white !important;
}

/* ===== BUTTONS ===== */
.stButton > button {
    border-radius: 12px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    color: white !important;
    border: none;
}

.stButton > button:hover {
    transform: scale(1.05);
}

/* ===== INPUT BOXES (WHITE BG + BLACK TEXT) ===== */
.stTextInput input {
    background-color: white !important;
    color: black !important;
    border-radius: 10px;
}

.stTextArea textarea {
    background-color: white !important;
    color: black !important;
    border-radius: 10px;
}

/* ===== LABELS ===== */
label {
    color: white !important;
}

/* ===== METRIC CARDS ===== */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.08);
    padding: 18px;
    border-radius: 15px;
    min-height: 110px;
}

/* Allow metric value to fully display */
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    white-space: normal !important;
}
}

/* ===== ALERT BOXES ===== */
.stAlert {
    border-radius: 12px;
}

/* ===== PROGRESS BAR ===== */
.stProgress > div > div > div {
    background-color: #00c6ff;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# GLOBAL LOGIN HEADER (ONLY BEFORE LOGIN)
# --------------------------------------------------
if st.session_state.get("user_id") is None:
    st.markdown("""
    <div style='text-align:center; padding:30px 0'>
        <h1 style="color:white; font-size:42px;">🎤 Welcome to AI Mock Interview</h1>
        <p style="font-size:18px; color:white;">
            Practice real interview scenarios powered by AI.
            Improve your communication, confidence, and technical clarity.
        </p>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# GLOBAL JS LISTENER
# --------------------------------------------------
html(
    """
    <script>
    window.addEventListener("message", (event) => {
        if (event.data?.type === "VIDEO_RECORDED") {
            window.Streamlit.setComponentValue(event.data);
        }
    });
    </script>
    """,
    height=0
)

video_event = html(
    """
    <script>
    const sendToStreamlit = (data) => {
        window.parent.postMessage(
            {
                isStreamlitMessage: true,
                type: "streamlit:setComponentValue",
                value: data
            },
            "*"
        );
    };

    window.addEventListener("message", (event) => {
        if (event.data?.type === "VIDEO_RECORDED") {
            sendToStreamlit(event.data);
        }
    });
    </script>
    """,
    height=0,
)

video_event = st.session_state.get("video_receiver")

if video_event and isinstance(video_event, dict):
    if "recorded_videos" not in st.session_state:
        st.session_state["recorded_videos"] = {}

    st.session_state["recorded_videos"][
        video_event["question_id"]
    ] = video_event["data"]

    st.session_state["video_receiver"] = None


# --------------------------------------------------
# SESSION STATE INITIALIZATION
# --------------------------------------------------
DEFAULT_STATE = {
    "auth_page": "login",
    "page": "welcome",
    "user_id": None,
    "user_email": None,
    "role": None,
    "difficulty": None,
    "session_id": None,
    "questions": [],
    "current_q": 0,
    "spoken_q": -1
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------
# AUTH FLOW
# --------------------------------------------------
if st.session_state["user_id"] is None:

    if st.session_state["auth_page"] == "login":
        login_page(supabase)

    elif st.session_state["auth_page"] == "signup":
        signup_page(supabase)

    else:
        st.session_state["auth_page"] = "login"
        st.rerun()


# --------------------------------------------------
# MAIN APP FLOW
# --------------------------------------------------
else:
    if st.session_state["page"] == "welcome":
        welcome_page()

    elif st.session_state["page"] == "setup":
        interview_setup_page()

    elif st.session_state["page"] == "interview":
        interview_page()

    elif st.session_state["page"] == "results":
        results_page()

    else:
        st.error("Unknown page state")
