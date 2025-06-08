# streamlit_app/login.py

import streamlit as st
import base64
from pathlib import Path

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Path to your local banner image
banner_path = Path(__file__).parent / "images" / "company_logo4.png"

def login_page():
    # Initialize 'authorized' in session state if not already present
    if "authorized" not in st.session_state:
        st.session_state["authorized"] = False

    # page-specific CSS overrides
    st.markdown(
        """
        <style>
        /* push the banner down just a little */
        .login-banner {
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }
        /* rest of your button styles… */
        .stButton>button {
            background-color: #4169e1 !important;
            color: #ffffff !important;
            border-radius: 5px !important;
            width: 100% !important;
            height: 40px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none !important;
            transition: background-color 0.2s ease-in-out;
        }
        .stButton>button:hover {
            background-color: #1E4DB7 !important;
        }
        /* Style for the success message */
        .stAlert {
            margin-top: 1rem; /* Adjust as needed */
            margin-bottom: 1rem; /* Adjust as needed */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # banner wrapped in its own CSS class
    b64 = image_to_base64(banner_path)
    st.markdown(
        f"""
        <div class="login-banner" style="text-align:left;">
          <img src="data:image/png;base64,{b64}"
               alt="CK Sports Physio"
               style="max-width:200px; width:80%;" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<h3>Login Required</h2>", unsafe_allow_html=True)

    # --- Authentication Step ---
    if not st.session_state["authorized"]:
        username = st.text_input("Username", key="login_username_auth")
        password = st.text_input("Password", type="password", key="login_password_auth")

        if st.button("Authenticate", key="authenticate_button"):
            if (username, password) in [
                ("melbourne_park_test", "@gemba#1"),
                ("Jessw", "Purplemonkeyd1shwasher"),
                ("o", "1"),
                ("BenG", "Shark1!"),
                ("SandraS", "1heartD@ta"),
                ("Leahc", "iheartMelb1"),
            ]:
                st.session_state["authorized"] = True
                st.success("Authenticated! Click Login to proceed.")
                st.rerun() # Rerun to hide auth fields and show login button
            else:
                st.error("Invalid credentials")

    # --- Login Step (after successful authentication) ---
    if st.session_state["authorized"] and not st.session_state["authenticated"]:
        st.success("Authenticated!")
        if st.button("Login", key="login_button"):
            st.session_state.authenticated = True
            st.rerun() # Rerun to trigger the main app in index.py