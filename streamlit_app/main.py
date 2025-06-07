# streamlit_app/main.py

import streamlit as st
import json
from pathlib import Path
from streamlit_calendar import calendar

from _common import apply_global_css, get_base64_image
from utils import get_client_db, load_data
from pages.new_program       import render_new_program
from pages.modify_program    import render_modify_program
from pages.client_status     import render_client_status
from pages.client_history    import render_client_history
from pages.exercise_database import render_exercise_database
from pages.settings          import render_settings

def main_app(page: str):
    apply_global_css()

    # hide Streamlit’s built-in page menu
    st.markdown(
        """<style>[data-testid="page-menu"]{display:none;}</style>""",
        unsafe_allow_html=True,
    )

    if page == "Home":
        _show_dashboard()
    elif page == "New Program":
        render_new_program()
    elif page == "Modify Program":
        render_modify_program()
    elif page == "Client Status":
        render_client_status()
    elif page == "Client History":
        render_client_history()
    elif page == "Exercise Database":
        render_exercise_database()
    elif page == "Settings":
        render_settings()
    else:
        st.error(f"Unknown page: {page}")

def _show_dashboard():
    st.title("Prescription Calendar")

    conn = get_client_db()
    total_clients   = conn.execute("SELECT COUNT(*) FROM clients WHERE status='active'").fetchone()[0]
    programs        = list((Path(__file__).parent / "patient_pdfs").rglob("*.json"))
    total_programs  = len(programs)
    total_exercises = len(load_data())

    images_dir      = Path(__file__).parent / "images"
    icons = {
        "clients":   images_dir / "group.png",
        "programs":  images_dir / "plus-circle.png",
        "exercises": images_dir / "database.png",
    }

    # build three columns
    c1, c2, c3 = st.columns(3)

    # helper to render icon + metric in one row
    def render_kpi(col, icon_path, label, value):
        # two sub‐columns: icon (small) | metric (big)
        i_col, m_col = col.columns([1, 4])
        if icon_path.exists():
            b64 = get_base64_image(icon_path)
            i_col.image(f"data:image/png;base64,{b64}", width=60)
        m_col.metric(label=label, value=value)

    render_kpi(c1, icons["clients"],   "Total Clients",   total_clients)
    render_kpi(c2, icons["programs"],  "Total Programs",  total_programs)
    render_kpi(c3, icons["exercises"], "Total Exercises", total_exercises)

    # now the calendar...
    events = []
    colour_map = {"Rehab":"#FF9999","Prehab":"#99FF99","Recovery":"#9999FF"}
    for p in programs:
        data  = json.loads(p.read_text())
        dt    = data["prescription_date"]
        typ   = data["rehab_type"]
        title = f"{data['firstname']} {data['lastname']} – {typ}"
        events.append({
            "title": title,
            "start": dt, "end": dt,
            "color": colour_map.get(typ, "#CCCCCC")
        })

    calendar(events=events, key="prog_cal")


if __name__ == "__main__":
    st.error("Please run via index.py, not directly.")
