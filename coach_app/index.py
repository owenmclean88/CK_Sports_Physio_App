import sys, os
# add the parent (ck_app1/) so we can import streamlit_app.*
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from login_coach    import login_page
from coach_status   import render_coach_status

st.set_page_config(
    page_title="Coach Portal",
    page_icon="💪",
    layout="wide",
)

if "authenticated_coach" not in st.session_state:
    st.session_state["authenticated_coach"] = False

if not st.session_state["authenticated_coach"]:
    login_page()
    st.stop()

# once logged in, hand off the coach_id
render_coach_status(st.session_state["coach_id"])
