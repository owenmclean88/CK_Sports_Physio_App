# streamlit_app/index.py

import streamlit as st
from pathlib import Path

from _common import apply_global_css
from login import login_page
from main import main_app

# ──────────────────────────────────────────────────────────────────────────────
# 1) AUTH GUARD: collapse sidebar on the login screen
# ──────────────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.set_page_config(
        page_title="Rehab, Prehab & Recovery App",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_global_css()
    login_page()
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# 2) NOW that you're authenticated, show your full sidebar
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rehab, Prehab & Recovery App",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_global_css()

# ──────────────────────────────────────────────────────────────────────────────
# 3) HIDE Streamlit’s built‐in multipage menu
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# 4) BUILD YOUR CUSTOM SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
sidebar = st.sidebar
logo_path = Path(__file__).parent / "images" / "company_logo4.png"
if logo_path.exists():
    sidebar.image(str(logo_path), use_container_width=True)
else:
    sidebar.error("Logo not found!")

PAGES = [
    "Home",
    "New Program",
    "Modify Program",
    "Client Status",
    "Client History",
    "Exercise Database",
    "Injury Audit",
    "Settings",
]

# Initialize "page" and "_page_changed" flag
if "page" not in st.session_state:
    st.session_state["page"] = "Home"
    st.session_state["_page_changed"] = True # Mark true for initial load

current_page_from_state = st.session_state["page"]

for p in PAGES:
    if sidebar.button(p, key=p):
        if st.session_state["page"] != p: # Only set flag if page is actually changing
            st.session_state["page"] = p
            st.session_state["_page_changed"] = True
        else:
            st.session_state["_page_changed"] = False # Page didn't change
        # Force a rerun if the page changed to reflect new state
        st.rerun() # <--- Changed from st.experimental_rerun() to st.rerun()

# If the page didn't change via button click in this rerun, reset the flag
# This might not be strictly necessary with st.rerun(), but harmless for now.
if "page" in st.session_state and st.session_state["page"] == current_page_from_state:
     st.session_state["_page_changed"] = False


# ──────────────────────────────────────────────────────────────────────────────
# 5) DISPATCH INTO YOUR MAIN APP
# ──────────────────────────────────────────────────────────────────────────────
main_app(st.session_state["page"])