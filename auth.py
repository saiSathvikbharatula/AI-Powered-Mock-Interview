# auth.py
import streamlit as st


def login_page(supabase):
    st.subheader("Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state["user_id"] = res.user.id
            st.session_state["user_email"] = res.user.email
            st.session_state["page"] = "welcome"
            st.success("Logged in successfully!")
            st.rerun()

        except Exception:
            st.error("Invalid email or password")

    st.markdown(
        "<small>Don't have an account?</small>",
        unsafe_allow_html=True
    )

    if st.button("Sign up"):
        st.session_state["auth_page"] = "signup"
        st.rerun()


def signup_page(supabase):
    st.subheader("Create Account")

    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_pass")

    if st.button("Create Account"):
        try:
            res = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if res.user is None:
                st.error("Auth user not created")
                return

            supabase.table("profiles").insert({
                "id": res.user.id,
                "email": email
            }).execute()

            st.success("Account created! Please login.")
            st.session_state["auth_page"] = "login"
            st.rerun()

        except Exception as e:
            st.error(f"Signup error: {e}")

    if st.button("Back to Login"):
        st.session_state["auth_page"] = "login"
        st.rerun()
