import os
from pathlib import Path
import streamlit as st
from _common import apply_global_css, get_base64_image
from utils    import get_client_db, load_data

# ───────────────────────────────────────────────────────────────
# locate your top-level assets
# ───────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
IMAGES_DIR = ROOT / "images"
PDF_DIR    = ROOT / "patient_pdfs"

# ───────────────────────────────────────────────────────────────
# callback for icon buttons
# ───────────────────────────────────────────────────────────────
def nav_to(page_name: str):
    st.session_state.page = page_name
    # no need for st.rerun(); on_click will trigger a rerun automatically

# ───────────────────────────────────────────────────────────────
# KPI helpers (unchanged)
# ───────────────────────────────────────────────────────────────
def get_unique_user_count(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE status='active'")
    return len({r[0] for r in cur.fetchall()})

def load_existing_patients():
    pts = {}
    if PDF_DIR.exists():
        for d in os.listdir(PDF_DIR):
            if d == "archived_clients": continue
            pts[d] = [f for f in os.listdir(PDF_DIR / d) if f.endswith(".json")]
    return pts

# ───────────────────────────────────────────────────────────────
# Main home‐page renderer
# ───────────────────────────────────────────────────────────────
def display_home_page():
    apply_global_css()

    # hide built-in sidebar here
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none;}</style>",
        unsafe_allow_html=True,
    )

    # header + logo
    logo = IMAGES_DIR / "company_logo4.png"
    if logo.exists():
        b64 = get_base64_image(logo)
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:20px;">
          <img src="data:image/png;base64,{b64}" width="150" alt="Logo"/>
          <h1 style="margin-left:20px;">Rehab, Prehab & Recovery App</h1>
        </div>
        <p>Welcome Cath King 👋. Click an icon below to navigate.</p>
        """, unsafe_allow_html=True)
    else:
        st.error("Logo not found at images/company_logo4.png")

    # icon buttons
    icons = {
        "new_prescription":    IMAGES_DIR / "plus-circle.png",
        "modify_prescription": IMAGES_DIR / "refresh.png",
        "client_history":      IMAGES_DIR / "group.png",
        "exercise_database":   IMAGES_DIR / "database.png",
        "settings":            IMAGES_DIR / "settings.png",
    }
    buttons = [
        ("New Program",        "new_prescription",   "New Program"),
        ("Modify Program",     "modify_prescription","Modify Program"),
        ("Client Status",      "client_history",     "Client Status"),
        ("Exercise Database",  "exercise_database",  "Exercise Database"),
        ("Settings",           "settings",           "Settings"),
    ]
    cols = st.columns(len(buttons))
    for col, (label, key, page_name) in zip(cols, buttons):
        with col:
            ico = icons[key]
            if ico.exists():
                b64 = get_base64_image(ico)
                st.markdown(
                    f"<div style='text-align:center;'><img src='data:image/png;base64,{b64}' width='80'/></div>",
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f"Missing icon: {key}")
            st.button(label, key=key, on_click=nav_to, args=(page_name,))

    # KPIs at the bottom
    conn            = get_client_db()
    total_clients   = get_unique_user_count(conn)
    total_programs  = sum(len(v) for v in load_existing_patients().values())
    total_exercises = len(load_data())

    st.markdown("""
      <style>
        .kpi-container{display:flex;justify-content:space-around;margin-top:50px;}
        .kpi-box{text-align:center;}
        .kpi-number{font-size:100px;font-weight:bold;}
        .kpi-label{font-size:20px;color:gray;}
      </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
      <div class="kpi-container">
        <div class="kpi-box">
          <div class="kpi-number">{total_clients}</div>
          <div class="kpi-label">Total Clients</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-number">{total_programs}</div>
          <div class="kpi-label">Total Programs</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-number">{total_exercises}</div>
          <div class="kpi-label">Total Exercises</div>
        </div>
      </div>
    """, unsafe_allow_html=True)
