# streamlit_app/pages/04_Client_History.py

import streamlit as st
from _common import apply_global_css, page_header
from pathlib import Path
import os
import json
import pandas as pd
from datetime import date, timedelta

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT      = Path(__file__).parent.parent
PDF_DIR  = PROJECT_ROOT / 'patient_pdfs'
ICON     = PROJECT_ROOT / 'images' / 'group.png'

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def load_existing_patients():
    patients = {}
    if PDF_DIR.exists():
        for folder in os.listdir(PDF_DIR):
            if folder == 'archived_clients':
                continue
            json_files = [f for f in os.listdir(PDF_DIR / folder) if f.endswith('.json')]
            patients[folder] = json_files
    return patients

def format_exercises(exs):
    movement_dict = {}
    for e in exs:
        mt = e.get('movement_type', '')
        movement_dict.setdefault(mt, []).append(e.get('exercise', ''))
    text = ""
    for mt, lst in movement_dict.items():
        text += f"{mt}: " + ", ".join(lst) + "\n"
    return text

# ──────────────────────────────────────────────────────────────────────────────
# Main render function
# ──────────────────────────────────────────────────────────────────────────────
def render_client_history():
    apply_global_css()
    page_header("Client History", icon_path=ICON)

    st.write(
        '<span style="color: grey;">Use the dropdowns below to filter the table displayed.</span>',
        unsafe_allow_html=True
    )

    # Filters
    existing = load_existing_patients()
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])
    client_filter    = col1.selectbox("Client Name", options=[""] + list(existing.keys()), key="history_client")
    rehab_filter     = col2.selectbox("Session Type", options=["", "Prehab", "Rehab", "Recovery"], key="history_rehab")
    start_date       = col3.date_input("Start Date", value=date.today() - timedelta(days=180), key="history_start")
    end_date         = col4.date_input("End Date",   value=date.today(),                          key="history_end")

    # Load all records into a DataFrame
    records = []
    for folder, files in existing.items():
        for fname in files:
            path = PDF_DIR / folder / fname
            with open(path, "r") as f:
                d = json.load(f)
            d["patient_name"]      = folder
            d["prescription_date"] = pd.to_datetime(d["prescription_date"]).date()
            d["exercises"]         = d.get("exercises", [])
            records.append(d)

    if not records:
        st.write("No client history found.")
        return

    df = pd.DataFrame(records)

    # Apply filters
    if client_filter:
        df = df[df["patient_name"] == client_filter]
    if rehab_filter:
        df = df[df["session_type"] == rehab_filter]
    df = df[
        (df["prescription_date"] >= start_date) &
        (df["prescription_date"] <= end_date)
    ]

    # Sort and format
    df = df.sort_values(by="prescription_date", ascending=False)
    df["Date"]      = df["prescription_date"]
    df["Exercises"] = df["exercises"].apply(format_exercises)

    # Select and rename columns for display
    display = df[["Date", "patient_name", "session_type", "rehab_type", "Exercises"]].rename(
        columns={
            "patient_name": "Client Name",
            "session_type": "Session Type",
            "rehab_type":   "Session Name"
        }
    )

    st.dataframe(display, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_client_history()
