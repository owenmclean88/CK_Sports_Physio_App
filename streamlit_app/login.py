import streamlit as st
import base64
from pathlib import Path

LOGO = Path(__file__).parent / "images" / "company_logo4.png"

def _b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()

def login_page():
    st.markdown("""
      <style>
        .stButton>button {width:100%; background:#4169e1; color:#fff;}
        .stButton>button:hover {background:#1e4db7;}
      </style>
    """, unsafe_allow_html=True)

    if LOGO.exists():
        b = _b64(LOGO)
        st.markdown(f"<img src='data:image/png;base64,{b}' width='150'/>", unsafe_allow_html=True)

    st.markdown("### Login Required", unsafe_allow_html=True)
    user = st.text_input("Username")
    pwd  = st.text_input("Password", type="password")
    if st.button("Log in"):
        # simple check — swap in your real auth
        if user == "o" and pwd == "1":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
