# coach_app/login_coach.py

import sys, os
from pathlib import Path
import base64
import streamlit as st

# allow import of your main app's utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from streamlit_app.utils import get_client_db

def _img_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def login_page():
    # ----------------------------
    # 1) GLOBAL/CSS TWEAKS
    # ----------------------------
    st.markdown(
        """
        <style>
        /* hide footer & menu for a cleaner look */
        footer, #MainMenu { visibility: hidden; }
        /* expand main container */
        .appview-container .main { padding: 2rem 1rem; }
        /* text inputs a bit taller */
        .stTextInput>div>div>input { height: 2.5rem; }
        /* full-width solid blue button */
        .stButton>button {
          background-color: #4169e1 !important;
          color: #fff !important;
          border-radius: 6px !important;
          width: 100% !important;
          height: 2.75rem !important;
          font-size: 16px !important;
          font-weight: 600 !important;
          border: none !important;
        }
        .stButton>button:hover { background-color: #1E4DB7 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------
    # 2) LOGO
    # ----------------------------
    logo_path = Path(__file__).parent.parent / "streamlit_app" / "images" / "company_logo4.png"
    if logo_path.exists():
        b64 = _img_to_base64(logo_path)
        st.markdown(
            f"""
            <div style="text-align:center; margin-bottom:2rem;">
              <img src="data:image/png;base64,{b64}"
                   alt="CK Sports Physio Logo"
                   style="width:75%; max-width:250px;" />
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ----------------------------
    # 3) TITLE
    # ----------------------------
    st.markdown(
        """
        <h2 style="text-align:center; margin-bottom:1rem;">
          COACH PORTAL LOGIN
        </h2>
        """,
        unsafe_allow_html=True,
    )

    # ----------------------------
    # 4) CREDENTIAL FIELDS
    # ----------------------------
    user = st.text_input("Username", key="coach_login_user")
    pwd  = st.text_input("Password", type="password", key="coach_login_pass")

    # ----------------------------
    # 5) LOGIN BUTTON & AUTH
    # ----------------------------
    if st.button("Login"):
        conn = get_client_db()
        if not conn:
            st.error("Could not connect to the database.")
            return

        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM clients WHERE username=? AND password=? AND account_type='Coach'",
            (user.strip(), pwd),
        )
        row = cur.fetchone()
        if row:
            st.session_state["authenticated_coach"] = True
            st.session_state["coach_id"]            = row[0]
            st.rerun()
        else:
            st.error("Invalid username or password.")
