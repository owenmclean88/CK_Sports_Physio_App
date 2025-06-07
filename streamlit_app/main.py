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
    total_clients = conn.execute(
        "SELECT COUNT(*) FROM clients WHERE status='active'"
    ).fetchone()[0]

    programs = list((Path(__file__).parent / "patient_pdfs").rglob("*.json"))
    total_programs = len(programs)
    total_exercises = len(load_data())

    # where your icons live
    images_dir = Path(__file__).parent / "images"
    client_icon   = images_dir / "group.png"
    program_icon  = images_dir / "plus-circle.png"
    exercise_icon = images_dir / "database.png"

    # three columns: each shows an icon above the metric
    c1, c2, c3 = st.columns(3)

    with c1:
        if client_icon.exists():
            b64 = get_base64_image(client_icon)
            st.image(f"data:image/png;base64,{b64}", width=50)
        st.metric(label="Total Clients", value=total_clients)

    with c2:
        if program_icon.exists():
            b64 = get_base64_image(program_icon)
            st.image(f"data:image/png;base64,{b64}", width=50)
        st.metric(label="Total Programs", value=total_programs)

    with c3:
        if exercise_icon.exists():
            b64 = get_base64_image(exercise_icon)
            st.image(f"data:image/png;base64,{b64}", width=50)
        st.metric(label="Total Exercises", value=total_exercises)

    # build calendar events
    events = []
    colour_map = {"Rehab":"#FF9999","Prehab":"#99FF99","Recovery":"#9999FF"}
    for p in programs:
        data = json.loads(p.read_text())
        dt  = data["prescription_date"]
        typ = data["rehab_type"]
        title = f"{data['firstname']} {data['lastname']} – {typ}"
        events.append({
            "title": title,
            "start": dt, "end": dt,
            "color": colour_map.get(typ, "#CCCCCC")
        })

    st.markdown("### Prescription Calendar")
    calendar(events=events, key="prog_cal")

if __name__ == "__main__":
    st.error("Please run via index.py, not directly.")
