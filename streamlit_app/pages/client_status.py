# streamlit_app/pages/03_Client_Status.py

import streamlit as st
from _common import apply_global_css, page_header, get_base64_image, get_status_color
from utils import get_client_db
from pathlib import Path
import os
import json
from datetime import date

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT      = Path(__file__).parent.parent
CONTENT_DIR        = PROJECT_ROOT / 'images'
PATIENT_STATUS_DIR = PROJECT_ROOT / 'patient_status'

# ──────────────────────────────────────────────────────────────────────────────
# Helper: Save updated status back to JSON
# ──────────────────────────────────────────────────────────────────────────────
def save_training_status_to_json(client_id: str, new_status: str, last_updated: date,
                                 previous_status: str = None, previous_date: str = None):
    # Locate the client's folder based on their ID
    client_folder = next(
        (f for f in os.listdir(PATIENT_STATUS_DIR) if client_id in f),
        None
    )
    if not client_folder:
        st.error(f"Client folder not found for ID: {client_id}")
        return

    status_file = PATIENT_STATUS_DIR / client_folder / "status.json"
    if not status_file.exists():
        st.error(f"Status file not found for ID: {client_id}")
        return

    with open(status_file, 'r') as f:
        details = json.load(f)

    old_status = details.get("current_status", "")
    details["previous_status"] = previous_status or old_status
    details["previous_date"]   = previous_date or details.get("last_updated", "")
    details["current_status"]  = new_status
    details["last_updated"]    = str(last_updated)

    with open(status_file, 'w') as f:
        json.dump(details, f)

# ──────────────────────────────────────────────────────────────────────────────
# Helper: Load all athlete status records
# ──────────────────────────────────────────────────────────────────────────────
def fetch_existing_clients():
    existing = []
    # get athlete IDs
    conn = get_client_db()
    athlete_ids = {row[0] for row in conn.execute(
        "SELECT id FROM clients WHERE account_type='Athlete'"
    ).fetchall()}

    if PATIENT_STATUS_DIR.exists():
        for folder in os.listdir(PATIENT_STATUS_DIR):
            sf = PATIENT_STATUS_DIR / folder / "status.json"
            if sf.exists():
                with open(sf, 'r') as f:
                    d = json.load(f)
                    cid = d.get("client_id")
                    if cid in athlete_ids:
                        existing.append({
                            "client_id": cid,
                            "firstname":   d.get("firstname",""),
                            "lastname":    d.get("lastname",""),
                            "current_status": d.get("current_status","Full Training"),
                            "last_updated":   d.get("last_updated",""),
                            "previous_status":d.get("previous_status",""),
                            "previous_date":  d.get("previous_date","")
                        })
    return existing

# ──────────────────────────────────────────────────────────────────────────────
# Helper: Map status to a colour
# ──────────────────────────────────────────────────────────────────────────────
def get_status_color(status: str) -> str:
    return {
        "Full Training":      "green",
        "Modified Training":  "orange",
        "Rehab":              "purple",
        "No Training":        "red"
    }.get(status, "gray")

# ──────────────────────────────────────────────────────────────────────────────
# Main render function
# ──────────────────────────────────────────────────────────────────────────────
def render_client_status():
    apply_global_css()
    page_header("Client Status", icon_path=CONTENT_DIR / 'group.png')

    # Button to refresh list
    if st.button("Show Updated List"):
        st.experimental_rerun()

    # Load existing records
    clients = fetch_existing_clients()
    if not clients:
        st.write("No client status data available.")
        return

    # Group by current status
    groups = {
        "Full Training":      [],
        "Modified Training":  [],
        "Rehab":              [],
        "No Training":        []
    }
    for c in clients:
        groups.setdefault(c["current_status"], []).append(c)

    # Render each group
    for status, items in groups.items():
        if not items:
            continue
        st.markdown(f"## {status} Clients")
        for client in items:
            cid   = client["client_id"]
            name  = f"{client['firstname']} {client['lastname']}"
            prev  = client["previous_status"]
            pdate = client["previous_date"]

            col1, col2 = st.columns([3,1])
            # Display name with coloured dot
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; margin-bottom:5px;">
                <span style="width:15px; height:15px; background-color:{get_status_color(status)};
                                border-radius:50%; display:inline-block; margin-right:10px;"></span>
                <span style="font-size:1.2rem; font-weight:bold;">{name}</span>
                </div>
                <div style="font-size:0.9rem; color:#555;">
                <p>Last Updated: {pdate or 'N/A'}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # New status selector and update button
            with col2:
                key = f"new_status_{cid}"
                new = st.selectbox(
                    "New Status",
                    ["", "Full Training", "Modified Training", "Rehab", "No Training"],
                    key=key
                )
                if st.button("Update", key=f"upd_{cid}") and new:
                    save_training_status_to_json(
                        client_id=cid,
                        new_status=new,
                        last_updated=date.today(),
                        previous_status=client["current_status"],
                        previous_date=client["last_updated"]
                    )
                    st.success(f"Updated {name} → {new}")

            st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_client_status()
