# streamlit_app/pages/injury_audit.py

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
import plotly.express as px # Import Plotly for charting

from _common import apply_global_css, page_header # Import common UI elements

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Constants
# ──────────────────────────────────────────────────────────────────────────────
# Define ROOT as the 'streamlit_app' directory
# Path(__file__).parent is 'streamlit_app/pages/'
# Path(__file__).parent.parent is 'streamlit_app/'
ROOT = Path(__file__).parent.parent

PATIENT_PDF_DIR = ROOT / "patient_pdfs"
ICON_PATH = ROOT / "images" / "chart-bar.png" # Assuming you have a chart-bar.png in your images folder

# ──────────────────────────────────────────────────────────────────────────────
# Data Loading and Processing for Audit
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_program_data_for_audit():
    """
    Loads program data from JSON files for the injury audit.
    Extracts the 'body_part' of the first exercise and 'rehab_type' for each program.
    """
    program_records = []

    if not PATIENT_PDF_DIR.exists():
        st.warning(f"Patient PDF directory not found: {PATIENT_PDF_DIR}. No program data to load.")
        return pd.DataFrame(columns=['body_part', 'rehab_type'])

    # Iterate through each client folder in the patient_pdfs directory
    for client_folder_name in os.listdir(PATIENT_PDF_DIR):
        client_folder_path = PATIENT_PDF_DIR / client_folder_name

        if client_folder_path.is_dir() and client_folder_name != "archived_clients":
            # Iterate through JSON files in each client's folder (each represents a program)
            for program_file_path in client_folder_path.iterdir():
                if program_file_path.suffix == ".json":
                    try:
                        with open(program_file_path, 'r', encoding='utf-8') as f:
                            program_data = json.load(f)

                        rehab_type = program_data.get("session_type", "Unknown Session Type") # Use session_type
                        exercises = program_data.get("exercises", [])

                        first_exercise_body_part = "Unknown Body Part"
                        if exercises and isinstance(exercises, list) and len(exercises) > 0:
                            first_exercise = exercises[0]
                            if isinstance(first_exercise, dict):
                                first_exercise_body_part = first_exercise.get("body_part", "Unknown Body Part")
                                # Clean up if body_part is empty or None
                                if not first_exercise_body_part:
                                    first_exercise_body_part = "Unknown Body Part"

                        program_records.append({
                            "body_part": first_exercise_body_part,
                            "rehab_type": rehab_type
                        })
                    except json.JSONDecodeError:
                        st.warning(f"Skipping malformed JSON file: {program_file_path}")
                    except Exception as e:
                        st.warning(f"Error processing {program_file_path}: {e}")

    return pd.DataFrame(program_records)

# ──────────────────────────────────────────────────────────────────────────────
# Main Render Function
# ──────────────────────────────────────────────────────────────────────────────
def render_injury_audit():
    apply_global_css()
    page_header("Injury Audit", icon_path=ICON_PATH)

    st.write("### Programs by Initial Body Part & Session Type")

    program_df = load_program_data_for_audit()

    if program_df.empty:
        st.info("No program data found or processed to display the audit. Please ensure programs are created and saved.")
        return

    # Count programs per body part and rehab type
    # We count the occurrences of each (body_part, rehab_type) pair
    chart_data = program_df.groupby(['body_part', 'rehab_type']).size().reset_index(name='count')

    # Create the stacked bar chart using Plotly Express
    fig = px.bar(
        chart_data,
        x='body_part',
        y='count',
        color='rehab_type', # This creates the stacked bars
        title='Count of Programs Prescribed by Initial Body Part and Session Type',
        labels={'body_part': 'Body Part (First Exercise)', 'count': 'Number of Programs', 'rehab_type': 'Session Type'},
        hover_data={'count': True}, # Show count on hover
        category_orders={"rehab_type": ["Prehab", "Rehab", "Recovery", "Unknown Session Type"]}, # Maintain consistent order
    )

    # Customize layout for better readability
    fig.update_layout(
        xaxis_title="Body Part (First Exercise)",
        yaxis_title="Number of Programs",
        legend_title="Session Type",
        font=dict(family="Inter", size=12),
        bargap=0.2, # Gap between bars
        xaxis={'categoryorder':'total descending'} # Order bars by total height descending
    )

    st.plotly_chart(fig, use_container_width=True)

    #st.markdown("---")
    st.write("### Raw Program Data (First Exercise Body Part)")
    st.dataframe(program_df, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point for direct execution (e.g., streamlit run 06_Injury_Audit.py)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(page_title="Injury Audit", layout="wide")
    render_injury_audit()