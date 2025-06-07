import streamlit as st
import sqlite3
import json
import os
import base64
from pathlib import Path

# Constants
LOGO_PATH = 'images/company_logo4.png'
PATIENT_STATUS_DIR = 'patient_status'
CONTENT_DIR = 'images'

# Function to encode the logo
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Set custom theme
def set_custom_theme():
    st.markdown(
        """
        <style>
        :root {
            --primary-color: #4169e1;
        }
        .stButton>button {
            width: 100%;
            background-color: var(--primary-color);
            border: 1px solid var(--primary-color);
            border-radius: 5px;
            color: #ffffff;
            cursor: pointer;
        }
        .stButton>button:hover {
            background-color: #1DA1F2;
            border: 1px solid #1DA1F2;
        }
        .welcome-banner {
            background-color: rgba(34, 139, 34, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            font-size: 1.1rem;
            margin-bottom: 20px;
        }
        .status-circle {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 10px;
        }
        .athlete-name {
            font-size: 1.2rem;
            font-weight: bold;
            display: inline-block;
        }
        .athlete-updated {
            font-size: 0.9rem;
            color: #888;
            margin-top: 0px;
        }
        .divider {
            border-bottom: 1px solid #ccc;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Fetch athletes assigned to a group for the coach
def fetch_athletes_in_group(conn, coach_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT gm.member_id
        FROM group_members gm
        JOIN user_groups ug ON gm.group_id = ug.id
        WHERE gm.role = 'Athlete' AND ug.id IN (
            SELECT group_id FROM group_members WHERE member_id = ? AND role = 'Coach'
        )
    """, (coach_id,))
    return [row[0] for row in cursor.fetchall()]

# Fetch assigned athletes from the JSON status files
def fetch_assigned_athletes(conn, coach_id):
    athletes = []
    athlete_ids = fetch_athletes_in_group(conn, coach_id)

    # Iterate through all the files in the `client_status` directory
    if os.path.exists(PATIENT_STATUS_DIR):
        for folder_name in os.listdir(PATIENT_STATUS_DIR):
            folder_path = os.path.join(PATIENT_STATUS_DIR, folder_name)
            status_file_path = os.path.join(folder_path, "status.json")

            if os.path.exists(status_file_path):
                with open(status_file_path, 'r') as status_file:
                    athlete_data = json.load(status_file)

                    # Fetch only the athletes assigned to the coach's group
                    athlete_id = athlete_data.get("client_id")
                    if athlete_id in athlete_ids:
                        athletes.append({
                            "client_id": athlete_data.get("client_id"),
                            "firstname": athlete_data.get("firstname"),
                            "lastname": athlete_data.get("lastname"),
                            "current_status": athlete_data.get("current_status", "Full Training"),
                            "last_updated": athlete_data.get("last_updated"),
                            "previous_status": athlete_data.get("previous_status", ""),
                            "previous_date": athlete_data.get("previous_date", "")
                        })

    return athletes

# Authentication function
def authenticate_user(conn, email, password):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE email = ? AND password = ? AND account_type = 'Coach'", (email, password))
    result = cursor.fetchone()
    if result:
        return result[0]  # Return coach ID
    return None

# Function to get the color associated with a client status
def get_status_color(status):
    if status == "Full Training":
        return "green"
    elif status == "Modified Training":
        return "orange"
    elif status == "Rehab":
        return "purple"
    elif status == "No Training":
        return "red"
    else:
        return "gray"  # Default color if status is unknown or not set

# Render the client status page for the coach
def render_client_status_page(conn, coach_id):
    st.markdown(f"<div class='welcome-banner'>Welcome, Coach!</div>", unsafe_allow_html=True)
    
    logo_base64 = get_base64_image(LOGO_PATH)
    st.image(f"data:image/png;base64,{logo_base64}", width=150)

    # Fetch athletes assigned to the coach
    athletes = fetch_assigned_athletes(conn, coach_id)

    if not athletes:
        st.write("No athletes assigned.")
        return

    # Group athletes by status and display them
    grouped_athletes = {
        "Full Training": [],
        "Modified Training": [],
        "Rehab": [],
        "No Training": []
    }

    for athlete in athletes:
        grouped_athletes[athlete['current_status']].append(athlete)

    # Display each group with a colored status circle
    first_group = True
    for status, athletes in grouped_athletes.items():
        if athletes:
            if not first_group:
                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            st.markdown(f"### {status} Athletes")
            for athlete in athletes:
                status_color = get_status_color(athlete['current_status'])
                st.markdown(
                    f"<div style='display: flex; align-items: center;'>"
                    f"<span class='status-circle' style='background-color:{status_color};'></span>"
                    f"<p class='athlete-name'>{athlete['firstname']} {athlete['lastname']}</p>"
                    f"</div>"
                    f"<p class='athlete-updated'>Last updated: {athlete['last_updated']}</p>",
                    unsafe_allow_html=True
                )
            first_group = False

def main():
    set_custom_theme()
    logo_base64 = get_base64_image(LOGO_PATH)
    
    # Database connection
    conn = sqlite3.connect('client_database.db')

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        # Center login form
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; flex-direction: column;">
                <img src="data:image/png;base64,{logo_base64}" width="200">
            </div>
            """,
            unsafe_allow_html=True,
        )
        email = st.text_input("Email", key="email")
        password = st.text_input("Password", type="password", key="password")
        if st.button("Login"):
            coach_id = authenticate_user(conn, email, password)
            if coach_id:
                st.session_state.coach_id = coach_id
                st.session_state.logged_in = True
                st.experimental_rerun()  # Rerun the app to show the status page
            else:
                st.error("Invalid email or password.")
    else:
        render_client_status_page(conn, st.session_state["coach_id"])

if __name__ == "__main__":
    main()
