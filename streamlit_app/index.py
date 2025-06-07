# streamlit_app/index.py

import streamlit as st
from pathlib import Path

from _common       import apply_global_css
from login         import login_page
from main          import main_app

# ──────────────────────────────────────────────────────────────────────────────
# 1) AUTH GUARD: collapse sidebar on the login screen
# ──────────────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # only this first branch runs until you log in
    st.set_page_config(
        page_title="Rehab, Prehab & Recovery App",
        page_icon=str(Path(__file__).parent / "images" / "company_logo4.png"),
        layout="wide",
        initial_sidebar_state="collapsed",  # <-- collapsed for login
    )
    apply_global_css()
    login_page()
    st.stop()  # halt here until credentials are correct

# ──────────────────────────────────────────────────────────────────────────────
# 2) NOW that you're authenticated, show your full sidebar
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rehab, Prehab & Recovery App",
    page_icon=str(Path(__file__).parent / "images" / "company_logo4.png"),
    layout="wide",
    initial_sidebar_state="auto",        # <-- visible for the main app
)
apply_global_css()

# ──────────────────────────────────────────────────────────────────────────────
# 3) HIDE Streamlit’s built-in multipage menu
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
# 4) BUILD YOUR CUSTOM SIDEBAR (logo + blue buttons)
# ──────────────────────────────────────────────────────────────────────────────
sidebar = st.sidebar

# 4a) company logo
logo_path = Path(__file__).parent / "images" / "company_logo4.png"
if logo_path.exists():
    sidebar.image(str(logo_path), use_container_width=True)
else:
    sidebar.error("Logo not found!")

# 4b) full‐width buttons
PAGES = [
    "Home",
    "New Program",
    "Modify Program",
    "Client Status",
    "Client History",
    "Exercise Database",
    "Settings",
]

# make sure we have a default
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# render them
for p in PAGES:
    if sidebar.button(p, key=p):
        st.session_state["page"] = p

# ──────────────────────────────────────────────────────────────────────────────
# 5) DISPATCH INTO YOUR MAIN APP
# ──────────────────────────────────────────────────────────────────────────────
main_app(st.session_state["page"])
