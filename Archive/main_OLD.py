import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import os
import json
from fpdf import FPDF
import base64
import sqlite3
import random
import datetime

#---------------------------------------------------------------
# Constants
LOGO_PATH = 'images/company_logo4.png'
PDF_LOGO_PATH = 'images/company_logo3.png'
PDF_DIR = 'patient_pdfs'
PATIENT_STATUS_DIR = 'patient_status'
EXERCISE_IMG_DIR = 'exercise_images/'
CONTENT_DIR = 'images'
EXERCISE_DB_PATH = 'exercise_database.csv'
CLIENT_DB_PATH = 'client_database.db'  # Path to the SQLite database
USER_GROUPS_DB_PATH = 'user_groups.db' # Path to the SQLite database
#---------------------------------------------------------------
# Set custom theme
def set_custom_theme():
    st.set_page_config(layout="wide", page_title="Exercise Prescription", page_icon=":muscle:", initial_sidebar_state="collapsed")
    st.markdown("""
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
        .stButton>button:active {
            background-color: #00FFFF;
            border: 1px solid #00FFFF;
        }
        .stButton>button.selected {
            background-color: #00FFFF;
            color: #ffffff;
            border: 1px solid #00FFFF;
        }
        .sidebar-footer {
            text-align: center;
            font-size: small;
            font-style: italic;
            padding-top: 50px;
        }
        .stSidebar .css-1d391kg {
            padding-left: 20%;
            padding-right: 20%;
            padding-bottom: 20%;
        }
        .stTextArea label {
            font-size: 1.2rem;
        }
        .stTextArea textarea {
            font-size: 1.2rem;
        }
        </style>
    """, unsafe_allow_html=True)
#---------------------------------------------------------------
# Load icons
def load_icons():
    icons = {
        "new_prescription": Path(CONTENT_DIR) / 'plus-circle.png',
        "modify_prescription": Path(CONTENT_DIR) / 'refresh.png',
        "client_history": Path(CONTENT_DIR) / 'group.png',
        "exercise_database": Path(CONTENT_DIR) / 'database.png',
        "settings": Path(CONTENT_DIR) / 'settings.png'
    }
    return icons
#---------------------------------------------------------------
# Load data
def load_data():
    try:
        data = pd.read_csv(EXERCISE_DB_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        data = pd.read_csv(EXERCISE_DB_PATH, encoding='ISO-8859-1')
    
    if 'body_part' not in data.columns:
        st.error("The 'body_part' column is missing from the CSV file. Please check the CSV file.")
        st.stop()
    return data
#---------------------------------------------------------------
# Initialize SQLite database
def initialize_database():
    conn = sqlite3.connect(CLIENT_DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,  
            account_type TEXT,
            first_name TEXT,
            last_name TEXT,
            mobile TEXT,
            email TEXT,
            password TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()
#--------------------USER GROUPS-----------------------------------
# Function to create a user group in the database
def create_user_group(conn, group_name, selected_coaches, selected_athletes):
    cursor = conn.cursor()

    # Insert the new group
    cursor.execute("INSERT INTO user_groups (group_name, date_created) VALUES (?, ?)", (group_name, date.today()))
    group_id = cursor.lastrowid

    # Add selected coaches to the group
    for coach in selected_coaches:
        coach_id = coach.split(" (ID: ")[1][:-1]
        cursor.execute("INSERT INTO group_members (group_id, member_id, role) VALUES (?, ?, 'Coach')", (group_id, coach_id))

    # Add selected athletes to the group
    for athlete in selected_athletes:
        athlete_id = athlete.split(" (ID: ")[1][:-1]
        cursor.execute("INSERT INTO group_members (group_id, member_id, role) VALUES (?, ?, 'Athlete')", (group_id, athlete_id))

    conn.commit()

# Function to fetch all user groups and display them in a DataFrame
def fetch_all_groups(conn):
    cursor = conn.cursor()

    # Fetch group information, ensuring DISTINCT is properly used
    cursor.execute("""
        SELECT g.id AS group_id, g.group_name, g.date_created,
               GROUP_CONCAT(DISTINCT CASE WHEN gm.role = 'Coach' THEN c.first_name || ' ' || c.last_name END) AS coaches,
               GROUP_CONCAT(DISTINCT CASE WHEN gm.role = 'Athlete' THEN c.first_name || ' ' || c.last_name END) AS athletes
        FROM user_groups g
        LEFT JOIN group_members gm ON g.id = gm.group_id
        LEFT JOIN clients c ON gm.member_id = c.id
        GROUP BY g.id, g.group_name, g.date_created
    """)

    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["Group ID", "Group Name", "Date Created", "Coaches", "Clients"])
    return df


def initialize_user_groups_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_groups (
            group_id TEXT PRIMARY KEY,
            date_created DATE,
            group_name TEXT,
            coaches TEXT,  -- Store coach IDs as a comma-separated string
            clients TEXT   -- Store client IDs as a comma-separated string
        )
    ''')
    conn.commit()

# Function to fetch coaches with their IDs
def fetch_coach_names_with_ids(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, id FROM clients WHERE account_type = 'Coach' AND status = 'active'")
    return cursor.fetchall()

# Function to fetch athletes with their IDs
def fetch_athlete_names_with_ids(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, id FROM clients WHERE account_type = 'Athlete' AND status = 'active'")
    return cursor.fetchall()

def update_user_group(conn, group_id, group_name, selected_coaches, selected_athletes):
    cursor = conn.cursor()

    # Update the group name
    cursor.execute("UPDATE user_groups SET group_name = ? WHERE id = ?", (group_name, group_id))

    # Clear existing coaches and athletes for the group
    cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))

    # Add updated coaches to the group
    for coach in selected_coaches:
        if " (ID: " in coach:
            coach_id = coach.split(" (ID: ")[1][:-1]
            cursor.execute("INSERT INTO group_members (group_id, member_id, role) VALUES (?, ?, 'Coach')", (group_id, coach_id))

    # Add updated athletes to the group
    for athlete in selected_athletes:
        if " (ID: " in athlete:
            athlete_id = athlete.split(" (ID: ")[1][:-1]
            cursor.execute("INSERT INTO group_members (group_id, member_id, role) VALUES (?, ?, 'Athlete')", (group_id, athlete_id))

    conn.commit()
#---------------------------------------------------------------
# Function to initialize the client_status table
def initialize_client_status_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_status (
            client_id TEXT PRIMARY KEY,
            client_name TEXT,
            current_status TEXT,
            last_prescribed_program TEXT,
            last_updated DATE,
            metrics_days INTEGER DEFAULT 0,
            full_training_days INTEGER DEFAULT 0,
            modified_training_days INTEGER DEFAULT 0,
            rehab_days INTEGER DEFAULT 0,
            no_training_days INTEGER DEFAULT 0,
            previous_status TEXT DEFAULT '',
            previous_date DATE DEFAULT ''
        )
    ''')
    conn.commit()
#---------------------------------------------------------------
# Generate a unique client ID
def generate_client_id(conn):
    while True:
        client_id = str(random.randint(10000000, 99999999))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clients WHERE id=?", (client_id,))
        if cursor.fetchone()[0] == 0:
            return client_id
#---------------------------------------------------------------
def fetch_all_clients(conn, account_type=None):
    cursor = conn.cursor()
    if account_type:
        cursor.execute("SELECT id, account_type, first_name, last_name, mobile, email, password, status FROM clients WHERE account_type = ?", (account_type,))
    else:
        cursor.execute("SELECT id, account_type, first_name, last_name, mobile, email, password, status FROM clients")
    return cursor.fetchall()

#---------------------------------------------------------------
def add_new_client(conn, client_id, account_type, first_name, last_name, mobile, email, password, status='active'):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clients (id, account_type, first_name, last_name, mobile, email, password, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (client_id, account_type, first_name, last_name, mobile, email, password, status))
    conn.commit()

    # Create folder in patient_pdfs directory
    folder_name = f"{last_name}_{first_name}_{client_id}"  # Corrected from 'lastname' to 'last_name'
    pdf_folder_path = os.path.join(PDF_DIR, folder_name)
    os.makedirs(pdf_folder_path, exist_ok=True)

    # Create a default status JSON file in the patient_status directory
    status_folder_path = os.path.join(PATIENT_STATUS_DIR, folder_name)
    os.makedirs(status_folder_path, exist_ok=True)
    status_file_path = os.path.join(status_folder_path, "status.json")
    default_status = {
        "client_id": client_id,
        "firstname": first_name,
        "lastname": last_name,
        "current_status": "Full Training",  # Default to Full Training
        "last_updated": str(date.today()),
        "previous_status": "",
        "previous_date": ""
    }
    
    with open(status_file_path, 'w') as status_file:
        json.dump(default_status, status_file)

    return pdf_folder_path, status_folder_path

#---------------------------------------------------------------
# Encode image to base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")
#---------------------------------------------------------------
# Initialize session state
def initialize_session_state():
    if 'menu_choice' not in st.session_state:
        st.session_state.menu_choice = "Home"
    if 'exercises' not in st.session_state:
        st.session_state.exercises = [0]
    if 'prescription_type' not in st.session_state:
        st.session_state.prescription_type = 'new'
    if 'first_name' not in st.session_state:
        st.session_state.first_name = ''
    if 'last_name' not in st.session_state:
        st.session_state.last_name = ''
    if 'rehab_type' not in st.session_state:
        st.session_state.rehab_type = ''
    if 'extra_comments' not in st.session_state:
        st.session_state.extra_comments = ''
    if 'show_preview' not in st.session_state:
        st.session_state.show_preview = False
#---------------------------------------------------------------
# Utility functions
def add_exercise():
    st.session_state.exercises.append(len(st.session_state.exercises))
#---------------------------------------------------------------
def reset_session_state():
    st.session_state.exercises = [0]
    st.session_state.first_name = ''
    st.session_state.last_name = ''
    st.session_state.rehab_type = ''
    st.session_state.extra_comments = ''
    st.session_state.show_preview = False
    for key in list(st.session_state.keys()):
        if key.startswith('body_part_') or key.startswith('movement_type_') or key.startswith('sub_movement_type_') or key.startswith('exercise_') or key.startswith('notes_') or key.startswith('volume_'):
            del st.session_state[key]
#---------------------------------------------------------------
def save_pdf(pdf, lastname, firstname, rehab_type, prescription_date, selected_exercises, extra_comments, session_type, client_id):
    # Locate the existing folder for the client using the client ID
    folder_name = f"{lastname}_{firstname}_{client_id}"
    folder_path = os.path.join(PDF_DIR, folder_name)

    # Ensure the folder exists
    if not os.path.exists(folder_path):
        st.error(f"Client folder not found: {folder_path}")
        return None

    # File paths for JSON and PDF
    details_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.json"
    details_file_path = os.path.join(folder_path, details_file_name)

    pdf_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.pdf"
    pdf_file_path = os.path.join(folder_path, pdf_file_name)

    # Save the PDF to the existing client folder
    pdf.output(pdf_file_path)

    # Save prescription details as JSON
    prescription_details = {
        'firstname': firstname,
        'lastname': lastname,
        'rehab_type': rehab_type,
        'prescription_date': str(prescription_date),
        'exercises': selected_exercises,
        'extra_comments': extra_comments,
        'session_type': session_type
    }
    with open(details_file_path, 'w') as details_file:
        json.dump(prescription_details, details_file)

    return pdf_file_path
#------------------------
def get_total_programs(existing_patients):
    total_programs = 0
    for programs in existing_patients.values():
        total_programs += len(programs)
    return total_programs
#------------------------
def load_existing_patients():
    patients = {}
    if os.path.exists(PDF_DIR):
        for folder in os.listdir(PDF_DIR):
            # Skip archived clients folder
            if folder == 'archived_clients':
                continue

            patient_name = folder
            json_files = [f for f in os.listdir(os.path.join(PDF_DIR, folder)) if f.endswith('.json')]
            patients[patient_name] = json_files
    return patients

#--------------------------------------
def load_prescription(selected_json):
    patient_name, json_file = selected_json.split("/")
    with open(os.path.join(PDF_DIR, patient_name, json_file), 'r') as details_file:
        prescription_details = json.load(details_file)

    st.session_state['first_name'] = prescription_details['firstname']
    st.session_state['last_name'] = prescription_details['lastname']
    st.session_state['rehab_type'] = prescription_details['rehab_type']
    st.session_state['prescription_date'] = date.fromisoformat(prescription_details['prescription_date'])
    st.session_state['session_type'] = prescription_details.get('session_type', 'Rehab')
    st.session_state.exercises = list(range(len(prescription_details['exercises'])))
    st.session_state['extra_comments'] = prescription_details['extra_comments']

    for i, exercise in enumerate(prescription_details['exercises']):
        st.session_state[f'body_part_{i}'] = exercise['body_part']
        st.session_state[f'movement_type_{i}'] = exercise['movement_type']
        st.session_state[f'sub_movement_type_{i}'] = exercise['sub_movement_type']
        st.session_state[f'position_{i}'] = exercise['position']  # Ensure position is set
        st.session_state[f'exercise_{i}'] = exercise['exercise']
        st.session_state[f'notes_{i}'] = exercise['notes']
        st.session_state[f'volume_{i}'] = exercise['volume']

    st.rerun()

#------------------------SIDEBAR---------------------------------------
def create_sidebar():
    logo_base64 = get_base64_image(LOGO_PATH)
    
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; padding-bottom: 20px;">
            <img src="data:image/png;base64,{logo_base64}" style="width: 75%;">
        </div>
        """,
        unsafe_allow_html=True
    )

    menu_options = ["Home", "New Program", "Modify Program", "Client Status", "Client History", "Exercise Database", "Settings"]

    for option in menu_options:
        if st.sidebar.button(option):
            st.session_state.menu_choice = option

    st.sidebar.markdown(
        """
        <div style="text-align: center; padding-top: 20px; font-size: 9px; color: grey;">
            © 2024 OProductions
        </div>
        """,
        unsafe_allow_html=True
    )

#---------------------------------------------------------------
def manage_sidebar():
    if st.session_state.menu_choice == "Home":
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {
                    display: none;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        create_sidebar()

#------------------------------------------HOME PAGE ---------------------------------------------------------------
def display_home_page():
    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None
    
    if logo_base64:
        st.markdown(
            f"""
            <div style="text-align: left;">
                <img src='data:image/png;base64,{logo_base64}' style='width: 150px; margin-bottom: 20px;' alt='Company Logo'>
                <h1 style='margin: 0; padding: 0;'>Rehab, Prehab & Recovery App</h1>
            </div>
            <p style="padding-bottom: 20px;">Welcome Cath King 👋. Double click the buttons below to navigate to different sections of the App.</p>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error("Company logo not found. Please check the LOGO_PATH.")

    icons = load_icons()

    col1, col2, col3, col4, col5 = st.columns(5)
    for col, label, icon, page in zip(
            [col1, col2, col3, col4, col5],
            ["New Program", "Modify Program", "Client Status", "Exercise Database", "Settings"],
            ["new_prescription", "modify_prescription", "client_history", "exercise_database", "settings"],
            ["New Program", "Modify Program", "Client Status", "Exercise Database", "Settings"]
    ):
        with col:
            icon_path = icons[icon]
            if icon_path.exists():
                img_base64 = get_base64_image(icon_path)
                st.markdown(
                    f"<div class='icon-container'><img src='data:image/png;base64,{img_base64}' class='icon'></div>",
                    unsafe_allow_html=True
                )
            else:
                st.warning(f"Icon not found: {icon_path}")
            if st.button(label, key=f"{icon}_button"):
                st.session_state.menu_choice = page
                manage_sidebar()
                st.rerun()

    # Fetch total clients dynamically from the database
    conn = sqlite3.connect(CLIENT_DB_PATH)
    total_clients = get_unique_user_count(conn)
    conn.close()

    # Fetch existing patients to calculate total programs
    existing_patients = load_existing_patients()
    total_programs = get_total_programs(existing_patients)

    # Define total exercises (adjust this to how you calculate total exercises)
    total_exercises = 2095  # Placeholder value; replace it with actual calculation if needed

    st.markdown(""" 
        <style>
        .kpi-container {
            display: flex;
            justify-content: space-around;
            margin-top: 50px;
        }
        .kpi-box {
            text-align: center;
            margin: 0 10px;
        }
        .kpi-number {
            font-size: 100px;
            font-weight: bold;
        }
        .kpi-label {
            font-size: 20px;
            color: gray;
        }
        .icon-container {
            display: flex;
            justify-content: center;
            margin-bottom: 10px;
        }
        .icon {
            width: 80px;
            height: 80px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class='kpi-container'>
            <div class='kpi-box'>
                <div class='kpi-number'>{total_clients}</div>
                <div class='kpi-label'>Total Clients</div>
            </div>
            <div class='kpi-box'>
                <div class='kpi-number'>{total_programs}</div>
                <div class='kpi-label'>Total Programs</div>
            </div>
            <div class='kpi-box'>
                <div class='kpi-number'>{total_exercises}</div>
                <div class='kpi-label'>Total Exercises</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

#-----------------------EXERCISES DISPLAY---------------------------------------------------
def swap_exercises(index1, index2):
    # Define keys to swap for each exercise
    keys_to_swap = [
        'body_part', 'movement_type', 'sub_movement_type', 'position', 'exercise', 'volume', 'notes', 'progressions'
    ]
    
    for key in keys_to_swap:
        key1 = f"{key}_{index1}"
        key2 = f"{key}_{index2}"
        # Swap the session state values
        st.session_state[key1], st.session_state[key2] = st.session_state.get(key2, ""), st.session_state.get(key1, "")

def move_exercise_up(index):
    if index > 0:
        # Swap the exercises in the session state
        swap_exercises(index, index - 1)

def move_exercise_down(index):
    if index < len(st.session_state.exercises) - 1:
        # Swap the exercises in the session state
        swap_exercises(index, index + 1)

def delete_exercise(index):
    # Remove all keys associated with the exercise at the specified index
    keys_to_delete = [
        'body_part', 'movement_type', 'sub_movement_type', 'position', 'exercise', 'volume', 'notes', 'progressions'
    ]
    
    # Delete the specific exercise data from session state
    for key in keys_to_delete:
        key_to_remove = f"{key}_{index}"
        if key_to_remove in st.session_state:
            del st.session_state[key_to_remove]
    
    # Shift all subsequent exercises up
    for i in range(index + 1, len(st.session_state.exercises)):
        for key in keys_to_delete:
            st.session_state[f"{key}_{i-1}"] = st.session_state.get(f"{key}_{i}", "")
            if f"{key}_{i}" in st.session_state:
                del st.session_state[f"{key}_{i}"]
    
    # Remove the last exercise from the list
    st.session_state.exercises.pop()

def render_exercise_fields(data):
    selected_exercises = []

    for i in range(len(st.session_state.exercises)):
        cols1 = st.columns([0.25, 1, 1, 1, 1, 0.15, 0.15, 0.15])
        cols1[0].write(f"{i + 1}.")

        # Select fields
        body_part = cols1[1].selectbox(
            f'Body Part {i + 1}',
            [""] + list(data['body_part'].unique()),
            key=f'body_part_{i}',
            index=0
        )

        # Automatically select if only one movement type is available
        movement_data = data[data['body_part'] == body_part] if body_part else pd.DataFrame(columns=['movement_type'])
        movement_options = [""] + list(movement_data['movement_type'].unique())
        movement_type = cols1[2].selectbox(
            f'Movement Type {i + 1}',
            movement_options,
            key=f'movement_type_{i}',
            index=1 if len(movement_options) == 2 else 0
        )

        # Automatically select if only one sub-movement type is available
        sub_movement_data = movement_data[movement_data['movement_type'] == movement_type] if movement_type else pd.DataFrame(columns=['sub_movement_type'])
        sub_movement_options = [""] + list(sub_movement_data['sub_movement_type'].unique())
        sub_movement_type = cols1[3].selectbox(
            f'Sub Movement Type {i + 1}',
            sub_movement_options,
            key=f'sub_movement_type_{i}',
            index=1 if len(sub_movement_options) == 2 else 0
        )

        # Automatically select if only one position is available
        position_data = sub_movement_data[sub_movement_data['sub_movement_type'] == sub_movement_type] if sub_movement_type else pd.DataFrame(columns=['position'])
        position_options = [""] + list(position_data['position'].unique())

        # Handle saved position correctly
        saved_position = st.session_state.get(f'position_{i}', "")
        if saved_position and saved_position not in position_options:
            position_options.append(saved_position)

        position = cols1[4].selectbox(
            f'Position {i + 1}',
            position_options,
            key=f'position_{i}',
            index=position_options.index(saved_position) if saved_position in position_options else 0
        )

        # Up, Down, and Delete buttons
        with cols1[5]:
            if i > 0:  # Only show the Up button if it's not the first exercise
                st.button("↑", key=f"move_up_{i}", help="Move Up", on_click=move_exercise_up, args=(i,))
        with cols1[6]:
            if i < len(st.session_state.exercises) - 1:  # Only show the Down button if it's not the last exercise
                st.button("↓", key=f"move_down_{i}", help="Move Down", on_click=move_exercise_down, args=(i,))
        with cols1[7]:
            st.button("🗑️", key=f"delete_{i}", help="Delete Exercise", on_click=delete_exercise, args=(i,))

        cols2 = st.columns([0.25, 2, 2])
        # Automatically select if only one exercise is available
        exercise_data = position_data[position_data['position'] == position] if position else pd.DataFrame(columns=['exercise'])
        exercise_options = [""] + list(exercise_data['exercise'].unique())

        # Handle missing exercise gracefully
        saved_exercise = st.session_state.get(f'exercise_{i}', "")
        if saved_exercise and saved_exercise not in exercise_options:
            exercise_options.append(saved_exercise)

        exercise = cols2[1].selectbox(
            f'Exercise {i + 1}',
            exercise_options,
            key=f'exercise_{i}',
            index=exercise_options.index(saved_exercise) if saved_exercise in exercise_options else 0
        )

        volume = cols2[2].text_input(
            f'Volume {i + 1}',
            key=f'volume_{i}',
            value="" if exercise_data[exercise_data['exercise'] == exercise].empty else exercise_data[exercise_data['exercise'] == exercise].iloc[0]['volume']
        )

        cols3 = st.columns([0.25, 2, 2])
        notes = cols3[1].text_input(f'Notes {i + 1}', key=f'notes_{i}', value="")
        progressions = cols3[2].text_input(f'Progressions {i + 1}', key=f'progressions_{i}', value="")

        # Collect data for each exercise
        selected_exercises.append({
            'body_part': body_part,
            'movement_type': movement_type,
            'sub_movement_type': sub_movement_type,
            'position': position,
            'exercise': exercise,
            'volume': volume,
            'notes': notes,
            'progressions': progressions
        })

        # Divider line between exercises
        if i < len(st.session_state.exercises) - 1:
            st.divider()

    # Add Exercise button
    st.button('Add Exercise', on_click=add_exercise, key='add_exercise_button', help='Add a new exercise')

    return selected_exercises


#----------------------------------------------------------------------------------
def remove_highest_exercise():
    if len(st.session_state.exercises) > 1:
        st.session_state.exercises.pop()

#----------------------------------------------------------------------------------
def get_unique_user_count(conn):
    # Fetch all active clients from the database
    clients = fetch_all_clients(conn)
    # Calculate the unique count based on client IDs
    return len(set(client[0] for client in clients))  # Assuming the first element in each tuple is the client ID
#----------------------------------------------------------------------------------
def generate_pdf(pdf, selected_exercises):
    pdf.image(PDF_LOGO_PATH, 10, 8, 33)
    
    pdf.set_font("Arial", size=12)
    pdf.set_xy(150, 10)
    pdf.multi_cell(50, 10, "Catherine King\nSports Physiotherapist\n0438503185", align='R')
    
    pdf.set_xy(10, 50)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=st.session_state['rehab_type'], ln=True, align='L')
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 5, txt=f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}", ln=True, align='L')
    pdf.cell(200, 5, txt=f"Prescription Date: {st.session_state['prescription_date']}", ln=True, align='L')
    
    pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
    pdf.ln(10)

    pdf.set_font("Arial", size=10)
    for movement_type in set(ex['movement_type'] for ex in selected_exercises):
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=movement_type, ln=True)
        pdf.set_font("Arial", size=10)
        
        for exercise in selected_exercises:
            if exercise['movement_type'] == movement_type:
                text = f"{exercise['exercise']}\nBody Part: {exercise['body_part']}\nPosition: {exercise['position']}\nVolume: {exercise['volume']}\nNotes: {exercise['notes']}\nProgressions: {exercise['progressions']}"
                current_y = pdf.get_y()
                pdf.multi_cell(150, 5, txt=text, align='L')
                
                if exercise['exercise']:
                    image_path_jpg = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.jpg"
                    image_path_png = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.png"
                    image_path = None
                    if os.path.exists(image_path_jpg):
                        image_path = image_path_jpg
                    elif os.path.exists(image_path_png):
                        image_path = image_path_png

                    if image_path:
                        pdf.image(image_path, x=160, y=current_y, w=30, h=30)
                
                pdf.ln(5)
                        
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Extra Comments", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=st.session_state['extra_comments'], align='L')

#-----------------------------------NEW PROGRAM PAGE------------------------------------------------------------
def render_new_prescription_page(data, conn):
    plus_icon_path = Path(CONTENT_DIR) / 'plus-circle.png'
    plus_icon_base64 = get_base64_image(plus_icon_path) if os.path.exists(plus_icon_path) else None

    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + plus_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if plus_icon_base64 else ''}
                <h1 style='margin: 0;'>New Program</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    # Custom CSS for buttons
    st.markdown("""
        <style>
        .custom-button {
            width: 100%;
            background-color: #4169e1;
            color: white;
            border: 1px solid #4169e1;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
            font-size: 16px;
            cursor: pointer;
        }
        .custom-button:hover {
            background-color: #1E4DB7;
            border-color: #1E4DB7;
        }
        </style>
    """, unsafe_allow_html=True)

    # Fetch only athletes from the database
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name FROM clients WHERE status = 'active' AND account_type = 'Athlete'")
    clients = cursor.fetchall()

    # Create a list of formatted client names to show in the dropdown
    client_options = [f"{client[1]} {client[2]} (ID: {client[0]})" for client in clients]

    # Select client from dropdown
    col1, col2, col3 = st.columns([2, 2, 1])
    selected_client = col1.selectbox('Select Client', options=[""] + client_options, key='selected_client')

    # Automatically set session state for first and last name based on selection
    client_id = None
    if selected_client:
        client_id = selected_client.split("(ID: ")[1][:-1]
        selected_client_info = next(client for client in clients if client[0] == client_id)
        st.session_state['first_name'] = selected_client_info[1]
        st.session_state['last_name'] = selected_client_info[2]

    session_type = col2.radio('Session Type', ['Prehab', 'Rehab', 'Recovery'], horizontal=True, key='session_type')
    
    col4, col5 = st.columns([2, 1])
    rehab_type = col4.text_input('Session Name', key='rehab_type')
    prescription_date = col5.date_input('Prescription Date', value=date.today(), key='prescription_date')

    st.write("### Exercises")

    # Render exercise fields
    selected_exercises = render_exercise_fields(data)

    st.markdown(
    """
    <h3 style='padding-top: 20px;'>Session Notes</h3>
    """, 
    unsafe_allow_html=True)

    extra_comments = st.text_area('Additional comments or notes relating to the session', key='extra_comments')

    # Check if conditions to show buttons are met
    has_selected_client = selected_client is not None and selected_client != ""
    has_session_name = st.session_state.get('rehab_type', "").strip() != ""
    has_minimum_exercise = any(ex['exercise'] for ex in selected_exercises)

    # Show PDF preview if conditions are met
    if has_selected_client and has_session_name and has_minimum_exercise:
        render_preview_section(selected_exercises)

        # Save and Export buttons
        save_session_button = st.button('Save Session Only', key='save_session_button', help='Save session without generating PDF')

        # Handle Save Session
        if save_session_button:
            save_session_to_json(client_id, selected_exercises)
            st.success(f'Session saved for {st.session_state["first_name"]} {st.session_state["last_name"]}')

        # Export to PDF and trigger download
        pdf = FPDF()
        pdf.add_page()
        generate_pdf(pdf, selected_exercises)

        pdf_output = pdf.output(dest='S').encode('latin1')
        download_button = st.download_button(
            label='Save & Export to PDF',
            data=pdf_output,
            file_name=f"{st.session_state['last_name']}_{st.session_state['first_name']}_{st.session_state['rehab_type']}_{st.session_state['prescription_date']}.pdf",
            mime='application/pdf',
            help='Save & Export to PDF'
        )

        if download_button:
            save_session_to_json(client_id, selected_exercises)
            st.success(f'Session saved and PDF exported for {st.session_state["first_name"]} {st.session_state["last_name"]}')

#------------------------------------------------------------------
def save_session_to_json(client_id, selected_exercises):
    # Save the session information to the client's folder in `patient_pdfs`
    folder_name = f"{st.session_state['last_name']}_{st.session_state['first_name']}_{client_id}"
    pdf_folder_path = os.path.join(PDF_DIR, folder_name)
    os.makedirs(pdf_folder_path, exist_ok=True)

    # Save session details as a JSON file
    details_file_name = f"{st.session_state['last_name']}_{st.session_state['first_name']}_{st.session_state['rehab_type']}_{st.session_state['prescription_date']}.json"
    details_file_path = os.path.join(pdf_folder_path, details_file_name)
    
    session_details = {
        'firstname': st.session_state['first_name'],
        'lastname': st.session_state['last_name'],
        'rehab_type': st.session_state['rehab_type'],
        'prescription_date': str(st.session_state['prescription_date']),
        'exercises': selected_exercises,
        'extra_comments': st.session_state['extra_comments'],
        'session_type': st.session_state['session_type']
    }
    with open(details_file_path, 'w') as details_file:
        json.dump(session_details, details_file)
#---------------------------------------------------------------------------------------------------    
def save_training_status_to_json(client_id, new_status, last_updated, previous_status=None, previous_date=None):
    # Locate the client's folder based on their ID
    client_folder = next(
        (folder for folder in os.listdir(PATIENT_STATUS_DIR) if client_id in folder),
        None
    )
    
    if not client_folder:
        st.error(f"Client folder not found for ID: {client_id}")
        return
    
    status_file_path = os.path.join(PATIENT_STATUS_DIR, client_folder, "status.json")
    
    # Read the existing status file
    if os.path.exists(status_file_path):
        with open(status_file_path, 'r') as status_file:
            status_details = json.load(status_file)
    else:
        st.error(f"Status file not found for ID: {client_id}")
        return
    
    # Update status details
    old_status = status_details.get("current_status", "")
    status_details["current_status"] = new_status
    status_details["last_updated"] = str(last_updated)
    status_details["previous_status"] = previous_status or old_status
    status_details["previous_date"] = previous_date or status_details.get("last_updated", "")
    
    # Save updated status back to JSON file
    with open(status_file_path, 'w') as status_file:
        json.dump(status_details, status_file)
    
#-----------------------------------------MODIFY PROGRAM PAGE----------------------------------------------------------    
def render_modify_prescription_page(data, existing_patients):
    refresh_icon_path = Path(CONTENT_DIR) / 'refresh.png'
    refresh_icon_base64 = get_base64_image(refresh_icon_path) if os.path.exists(refresh_icon_path) else None

    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + refresh_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if refresh_icon_base64 else ''}
                <h1 style='margin: 0;'>Modify Program</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    st.write("### Recall Saved Session")
    patient_name = st.selectbox('Select Patient', options=[""] + list(existing_patients.keys()))
    if patient_name:
        json_files = existing_patients.get(patient_name, [])
        program_names = [json_file.split('/')[-1] for json_file in json_files]
        selected_json = st.selectbox('Select Prescription', options=[""] + program_names)
        if selected_json and st.button('Load Program'):
            load_prescription(f"{patient_name}/{selected_json}")

    # Single row: Apply Modified Session To, Session Type, Session Name, Prescription Date
    col1, col2, col3, col4 = st.columns([0.25, 0.15, 0.45, 0.15])

    clients = list(existing_patients.keys())  # Fetch clients from existing patients
    if "apply_to_client" not in st.session_state:
        st.session_state.apply_to_client = patient_name  # Default to loaded patient name
    apply_to_client = col1.selectbox(
        'Apply Modified Session To',
        options=[""] + clients,
        key='apply_to_client',
        index=clients.index(patient_name) + 1 if patient_name in clients else 0
    )

    # Update `first_name` and `last_name` if a different client is selected
    if apply_to_client and apply_to_client != patient_name:
        selected_client_info = apply_to_client.split("_")
        st.session_state['first_name'] = selected_client_info[1]
        st.session_state['last_name'] = selected_client_info[0]

    # Session Type as a dropdown
    session_type_options = ['Prehab', 'Rehab', 'Recovery']
    session_type = col2.selectbox(
        'Session Type',
        options=[""] + session_type_options,
        key='session_type'
    )

    # Session Name and Prescription Date
    session_name = col3.text_input('Session Name', key='rehab_type')
    prescription_date = col4.date_input('Prescription Date', value=date.today(), key='prescription_date')

    st.write("### Exercises")
    selected_exercises = render_exercise_fields(data)

    st.markdown(
        """
        <h3 style='padding-top: 20px;'>Session Notes</h3>
        """, 
        unsafe_allow_html=True
    )

    extra_comments = st.text_area('Additional comments or notes relating to the session', key='extra_comments')

    # Check if conditions to show buttons and preview are met
    has_selected_client = apply_to_client is not None and apply_to_client != ""
    has_session_name = st.session_state.get('rehab_type', "").strip() != ""
    has_minimum_exercise = any(ex['exercise'] for ex in selected_exercises)

    # Show PDF preview if conditions are met
    if has_selected_client and has_session_name and has_minimum_exercise:
        render_preview_section(selected_exercises)

    # Save and Export buttons
    save_session_button = st.button('Save Session Only', key='save_session_modify_button', help='Save session without generating PDF')
    if save_session_button:
        client_id = apply_to_client.split("_")[-1]
        save_session_to_json(client_id, selected_exercises)
        st.success(f'Session saved for {st.session_state["first_name"]} {st.session_state["last_name"]}')

    # Export to PDF and trigger download
    pdf = FPDF()
    pdf.add_page()
    generate_pdf(pdf, selected_exercises)

    pdf_output = pdf.output(dest='S').encode('latin1')
    download_button = st.download_button(
        label='Save & Export to PDF',
        data=pdf_output,
        file_name=f"{st.session_state['last_name']}_{st.session_state['first_name']}_{st.session_state['rehab_type']}_{st.session_state['prescription_date']}.pdf",
        mime='application/pdf',
        help='Save & Export to PDF'
    )

    if download_button:
        client_id = apply_to_client.split("_")[-1]
        save_session_to_json(client_id, selected_exercises)
        st.success(f'Session saved and PDF exported for {st.session_state["first_name"]} {st.session_state["last_name"]}')

#-----------------------------Client Status Functions-----------------------------------
def initialize_client_status(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_status (
            client_id TEXT PRIMARY KEY,
            client_name TEXT,
            current_status TEXT,
            last_prescribed_program TEXT,
            last_updated DATE,
            metrics_days INTEGER DEFAULT 0,
            full_training_days INTEGER DEFAULT 0,
            modified_training_days INTEGER DEFAULT 0,
            rehab_days INTEGER DEFAULT 0,
            no_training_days INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

def fetch_client_status(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cs.client_id, cs.current_status, cs.last_prescribed_program, cs.last_updated,
               cs.metrics_days, cs.full_training_days, cs.modified_training_days, cs.rehab_days, cs.no_training_days,
               c.first_name, c.last_name
        FROM clients c
        LEFT JOIN client_status cs ON cs.client_id = c.id
    ''')
    return cursor.fetchall()

from datetime import datetime

def update_client_status(conn, client_id, new_status):
    cursor = conn.cursor()
    current_time = datetime.now()  # Get the current date and time

    # Get current data
    cursor.execute("SELECT current_status, last_updated FROM client_status WHERE client_id = ?", (client_id,))
    result = cursor.fetchone()

    if result:
        previous_status, last_updated = result
        
        # Update with new data, setting previous status & date if available
        cursor.execute('''
            UPDATE client_status 
            SET previous_status = ?, 
                previous_date = ?, 
                current_status = ?, 
                last_updated = ? 
            WHERE client_id = ?;
        ''', (previous_status if previous_status else new_status, last_updated if last_updated else current_time, new_status, current_time, client_id))
        
    else:
        # If no existing entry, insert a new one
        cursor.execute('''
            INSERT INTO client_status (client_id, current_status, last_updated) 
            VALUES (?, ?, ?);
        ''', (client_id, new_status, current_time))

    conn.commit()



def update_client_status_schema(conn):
    cursor = conn.cursor()
    # Ensure new columns are added if they don't exist
    try:
        cursor.execute('''
            ALTER TABLE client_status 
            ADD COLUMN previous_status TEXT DEFAULT '';
        ''')
    except sqlite3.OperationalError:
        pass  # Ignore if the column already exists

    try:
        cursor.execute('''
            ALTER TABLE client_status 
            ADD COLUMN previous_date DATE DEFAULT '';
        ''')
    except sqlite3.OperationalError:
        pass  # Ignore if the column already exists
    
    conn.commit()


import os
import json

def fetch_existing_clients(conn):
    existing_clients = []

    # Get a list of athlete IDs from the database
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE account_type = 'Athlete'")
    athlete_ids = {row[0] for row in cursor.fetchall()}

    # Iterate through each client folder in `PDF_DIR`
    if os.path.exists(PDF_DIR):
        for folder in os.listdir(PDF_DIR):
            client_folder = os.path.join(PDF_DIR, folder)
            status_file_path = os.path.join(client_folder, "status.json")

            # Check if status.json exists
            if os.path.exists(status_file_path):
                with open(status_file_path, 'r') as status_file:
                    client_data = json.load(status_file)
                    
                    # Only include if the client ID is an athlete
                    if client_data.get("client_id") in athlete_ids:
                        existing_clients.append({
                            "client_id": client_data.get("client_id"),
                            "firstname": client_data.get("firstname"),
                            "lastname": client_data.get("lastname"),
                            "current_status": client_data.get("current_status", "Full Training"),
                            "last_updated": client_data.get("last_updated"),
                            "previous_status": client_data.get("previous_status", ""),
                            "previous_date": client_data.get("previous_date", "")
                        })

    return existing_clients

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

#--------------------------------------------------------------------------- 
def render_preview_section(selected_exercises):
    with st.expander("Preview Program PDF", expanded=False):
        st.image(PDF_LOGO_PATH, width=100)
        st.write(f"<h2>{st.session_state['rehab_type']}</h2>", unsafe_allow_html=True)
        st.write(f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}")
        st.write(f"Prescription Date: {st.session_state['prescription_date']}")

        for movement_type in set(ex['movement_type'] for ex in selected_exercises):
            st.write(f"### {movement_type}")
            for exercise in selected_exercises:
                if exercise['movement_type'] == movement_type:
                    st.write(f"**{exercise['exercise']}**")
                    st.write(f"Body Part: {exercise['body_part']}")
                    st.write(f"Position: {exercise['position']}")
                    st.write(f"Volume: {exercise['volume']}")
                    st.write(f"Notes: {exercise['notes']}")
                    st.write(f"Progressions: {exercise['progressions']}")
                    
                    image_path_jpg = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.jpg"
                    image_path_png = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.png"
                    image_path = None
                    
                    if os.path.exists(image_path_jpg):
                        image_path = image_path_jpg
                    elif os.path.exists(image_path_png):
                        image_path = image_path_png
                    
                    if image_path:
                        st.image(image_path, width=100)
        
        st.write("### Extra Comments")
        st.write(st.session_state['extra_comments'])
        
#-----------------------------HISTROY PAGE----------------------------------------------
def render_client_history_page(existing_patients):
    group_icon_base64 = get_base64_image(Path(CONTENT_DIR) / 'group.png') if os.path.exists(Path(CONTENT_DIR) / 'group.png') else None
    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + group_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if group_icon_base64 else ''}
                <h1 style='margin: 0;'>Client History</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    st.write('<span style="color: grey;">Use the dropdowns below to filter the table displayed.</span>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])
    client_filter = col1.selectbox('Client Name', options=[""] + list(existing_patients.keys()))
    rehab_type_filter = col2.selectbox('Rehab Type', options=["", "Prehab", "Rehab", "Recovery"])
    start_date = col3.date_input('Start Date', value=date.today() - timedelta(days=6*30))
    end_date = col4.date_input('End Date', value=date.today())

    all_prescriptions = []
    for patient_name, files in existing_patients.items():
        for file in files:
            with open(os.path.join(PDF_DIR, patient_name, file), 'r') as details_file:
                prescription_details = json.load(details_file)
                prescription_details['file_name'] = file
                prescription_details['patient_name'] = patient_name
                all_prescriptions.append(prescription_details)

    df = pd.DataFrame(all_prescriptions)
    if client_filter:
        df = df[df['patient_name'] == client_filter]
    if rehab_type_filter:
        df = df[df['session_type'] == rehab_type_filter]  # Filter based on session type (Prehab, Rehab, Recovery)
    
    df = df[(df['prescription_date'] >= str(start_date)) & (df['prescription_date'] <= str(end_date))]
    df = df.sort_values(by='prescription_date', ascending=False)

    # Rename columns correctly to ensure proper mapping
    df = df.rename(columns={
        'prescription_date': 'Date',
        'patient_name': 'Client Name',
        'session_type': 'Session Type',  # This column should be "Prehab," "Rehab," or "Recovery"
        'rehab_type': 'Session Name',  # This should be the actual name of the session
        'exercises': 'Exercises'
    })[['Date', 'Client Name', 'Session Type', 'Session Name', 'Exercises']]

    # Function to format exercises in a readable manner
    def format_exercises(exercises):
        movement_dict = {}
        for ex in exercises:
            movement_type = ex['movement_type']
            if movement_type not in movement_dict:
                movement_dict[movement_type] = []
            movement_dict[movement_type].append(ex['exercise'])
        formatted = ""
        for movement_type, exercises in movement_dict.items():
            formatted += f"{movement_type}: " + ", ".join(exercises) + "\n"
        return formatted

    df['Exercises'] = df['Exercises'].apply(format_exercises)
    
    total_clients = df['Client Name'].nunique()
    total_programs = len(df)

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style='margin: 0;'>Program List</h3>
            <h4 style='margin: 0;'>Total Clients: {total_clients} | Total Programs: {total_programs}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.dataframe(df, use_container_width=True)


#---------------------------------------------------------------
def get_image_link(exercise):
    image_jpg = f"{EXERCISE_IMG_DIR}/{exercise}.jpg"
    image_png = f"{EXERCISE_IMG_DIR}/{exercise}.png"
    if os.path.exists(image_jpg):
        return f"<a href='{image_jpg}' target='_blank'>View Image</a>"
    elif os.path.exists(image_png):
        return f"<a href='{image_png}' target='_blank'>View Image</a>"
    else:
        return "No Image"
#---------------------------------------------------------------    
def render_exercise_database_page(data):
    database_icon_path = Path(CONTENT_DIR) / 'database.png'
    database_icon_base64 = get_base64_image(database_icon_path) if os.path.exists(database_icon_path) else None

    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + database_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if database_icon_base64 else ''}
                <h1 style='margin: 0;'>Exercise Database</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    st.write('<span style="color: grey;">Adding filters from the dropdowns will reduce the exercises displayed in the table to assist you in finding what you\'re looking for.</span>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 0.5])
    
    if col5.button('Clear All'):
        st.session_state['body_part_filter'] = ""
        st.session_state['movement_type_filter'] = ""
        st.session_state['sub_movement_type_filter'] = ""
        st.session_state['position_filter'] = ""

    # Convert all values in the dropdown columns to strings to prevent TypeError
    body_part_filter = col1.selectbox('Body Part', [""] + sorted(list(map(str, data['body_part'].unique()))), key='body_part_filter')
    movement_type_filter = col2.selectbox('Movement Type', [""] + sorted(list(map(str, data['movement_type'].unique()))), key='movement_type_filter')
    sub_movement_type_filter = col3.selectbox('Sub Movement Type', [""] + sorted(list(map(str, data['sub_movement_type'].unique()))), key='sub_movement_type_filter')
    position_filter = col4.selectbox('Position', [""] + sorted(list(map(str, data['position'].unique()))), key='position_filter')

    # Apply filters to the data
    if body_part_filter or movement_type_filter or sub_movement_type_filter or position_filter:
        filtered_data = data[
            (data['body_part'] == body_part_filter if body_part_filter else True) &
            (data['movement_type'] == movement_type_filter if movement_type_filter else True) &
            (data['sub_movement_type'] == sub_movement_type_filter if sub_movement_type_filter else True) &
            (data['position'] == position_filter if position_filter else True)
        ]
    else:
        filtered_data = data  # If no filters are selected, display the entire table

    # Rename columns and handle missing columns
    filtered_data = filtered_data.rename(columns={
        'body_part': 'Body Part',
        'movement_type': 'Movement Type',
        'sub_movement_type': 'Sub Movement Type',
        'position': 'Position',
        'exercise': 'Exercise',
        'volume': 'Volume',
        'notes': 'Notes',
    })

    # Add missing columns if necessary
    if 'Sub Movement Type' not in filtered_data.columns:
        filtered_data['Sub Movement Type'] = ""
    if 'Volume' not in filtered_data.columns:
        filtered_data['Volume'] = ""
    if 'Image' not in filtered_data.columns:
        filtered_data['Image'] = filtered_data['Exercise'].apply(get_image_link)

    # Reorder columns to move 'Volume' before 'Image'
    filtered_data = filtered_data[['Body Part', 'Movement Type', 'Sub Movement Type', 'Position', 'Exercise', 'Volume', 'Image', 'Notes']]

    # Select exercise to edit dropdown
    filtered_exercise_options = []
    if 'Body Part' in filtered_data.columns and 'Movement Type' in filtered_data.columns:
        filtered_exercise_options = [f"{row['Body Part']} - {row['Movement Type']} - {row['Sub Movement Type']} - {row['Position']} - {row['Exercise']}" for idx, row in filtered_data.iterrows()]
    
    edit_exercise_index = st.selectbox("Select Exercise to Edit", options=[""] + filtered_exercise_options)

    # Set custom CSS for table height, text wrapping, and equal column width for Notes
    st.markdown(
        """
        <style>
        .stDataFrame {
            max-height: 600px;  /* Increase the height of the table */
        }
        .stDataFrame tbody tr td {
            white-space: normal;  /* Wrap text in table cells */
        }
        .stDataFrame tbody tr td:nth-child(7), /* Notes column */
        .stDataFrame tbody tr td:nth-child(8) /* Notes column */ {
            width: 250px;  /* Set equal width for Notes columns */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Displaying the custom exercise list with hyperlinks and total count
    total_exercises = len(filtered_data)
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3>Exercise List</h3>
            <h4>Total Exercises: {total_exercises}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.dataframe(filtered_data, use_container_width=True)

    if edit_exercise_index:
        selected_exercise = filtered_data.iloc[filtered_exercise_options.index(edit_exercise_index) - 1]
        st.write(f"Editing Exercise: {selected_exercise['Exercise']}")
        with st.form(key=f'edit_form_{edit_exercise_index}'):
            body_part_edit = st.selectbox('Body Part', sorted(list(map(str, data['body_part'].unique()))), index=sorted(list(map(str, data['body_part'].unique()))).index(selected_exercise['Body Part']))
            movement_type_edit = st.selectbox('Movement Type', sorted(list(map(str, data[data['body_part'] == body_part_edit]['movement_type'].unique()))), index=sorted(list(map(str, data[data['body_part'] == body_part_edit]['movement_type'].unique()))).index(selected_exercise['Movement Type']))
            sub_movement_type_edit = st.selectbox('Movement Sub-Type', sorted(list(map(str, data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()))), index=sorted(list(map(str, data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()))).index(selected_exercise['Sub Movement Type']))
            position_edit = st.selectbox('Position', sorted(list(map(str, data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit) & (data['sub_movement_type'] == sub_movement_type_edit)]['position'].unique()))), index=sorted(list(map(str, data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit) & (data['sub_movement_type'] == sub_movement_type_edit)]['position'].unique()))).index(selected_exercise['Position']))
            exercise_edit = st.text_input('Exercise', value=selected_exercise['Exercise'])
            volume_edit = st.text_input('Volume', value="" if pd.isna(selected_exercise['Volume']) else selected_exercise['Volume'])
            notes_edit = st.text_area('Notes', value="" if pd.isna(selected_exercise['Notes']) else selected_exercise['Notes'])
            
            # Upload image
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png"])
            if uploaded_file:
                image_path = f"{EXERCISE_IMG_DIR}/{exercise_edit}.{uploaded_file.name.split('.')[-1]}"
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"Uploaded {uploaded_file.name} for exercise {exercise_edit}")
            
            # Display current image and delete option
            image_path_jpg = f"{EXERCISE_IMG_DIR}/{selected_exercise['Exercise']}.jpg"
            image_path_png = f"{EXERCISE_IMG_DIR}/{selected_exercise['Exercise']}.png"
            image_path = None
            
            if os.path.exists(image_path_jpg):
                image_path = image_path_jpg
            elif os.path.exists(image_path_png):
                image_path = image_path_png
            
            if image_path:
                st.image(image_path, use_column_width=True)
                delete_image = st.form_submit_button('Delete Image')
                if delete_image:
                    os.remove(image_path)
                    st.success(f"Deleted image for exercise {selected_exercise['Exercise']}")
            
            save_changes = st.form_submit_button('Save Changes')
            if save_changes:
                data.loc[selected_exercise.name, 'body_part'] = body_part_edit
                data.loc[selected_exercise.name, 'movement_type'] = movement_type_edit
                data.loc[selected_exercise.name, 'sub_movement_type'] = sub_movement_type_edit
                data.loc[selected_exercise.name, 'position'] = position_edit
                data.loc[selected_exercise.name, 'exercise'] = exercise_edit
                data.loc[selected_exercise.name, 'volume'] = volume_edit
                data.loc[selected_exercise.name, 'notes'] = notes_edit
                data.to_csv('exercise_database.csv', index=False)
                st.success('Exercise updated successfully!')
                st.rerun()

#-------------------------STATUS PAGE--------------------------------------
def render_client_status_page(conn):
    settings_icon_base64 = get_base64_image(Path(CONTENT_DIR) / 'group.png') if os.path.exists(Path(CONTENT_DIR) / 'group.png') else None
    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    # Header section
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + settings_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if settings_icon_base64 else ''}
                <h1 style='margin: 0;'>Client Status</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    # Show updated list button to refresh
    if st.button("Show Updated List"):
        st.rerun()

    # Fetch only athletes' IDs from the database
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM clients WHERE account_type = 'Athlete'")
    athlete_ids = [row[0] for row in cursor.fetchall()]

    # Fetch JSON files and filter by athlete_ids
    existing_clients = []
    if os.path.exists(PATIENT_STATUS_DIR):
        for folder in os.listdir(PATIENT_STATUS_DIR):
            folder_path = os.path.join(PATIENT_STATUS_DIR, folder)
            if os.path.isdir(folder_path):
                status_file_path = os.path.join(folder_path, "status.json")
                if os.path.exists(status_file_path):
                    with open(status_file_path, 'r') as status_file:
                        client_data = json.load(status_file)
                        if client_data.get("client_id") in athlete_ids:
                            existing_clients.append({
                                "client_id": client_data.get("client_id"),
                                "firstname": client_data.get("firstname"),
                                "lastname": client_data.get("lastname"),
                                "current_status": client_data.get("current_status", "Full Training"),
                                "last_updated": client_data.get("last_updated"),
                                "previous_status": client_data.get("previous_status", ""),
                                "previous_date": client_data.get("previous_date", "")
                            })

    if not existing_clients:
        st.write("No client status data available.")
        return

    # Define the display order for the sections and group clients
    grouped_clients = {
        "Rehab": [],
        "Modified Training": [],
        "No Training": [],
        "Full Training": []
    }

    for client in existing_clients:
        grouped_clients[client["current_status"]].append(client)

    # Render each group with a header if there are clients in that group
    for status, clients in grouped_clients.items():
        if not clients:
            continue  # Skip this group if there are no clients with this status

        # Header for each group
        st.markdown(f"## {status} Clients")

        for client in clients:
            client_id = client["client_id"]
            client_name = f"{client['firstname']} {client['lastname']}"
            current_status = client["current_status"]
            last_updated = client["last_updated"]
            previous_status = client["previous_status"]
            previous_date = client["previous_date"]

            col1, col2 = st.columns([2, 1])

            # Display client name with a status color dot and previous details
            status_color = get_status_color(current_status)  # Using current status for color
            col1.markdown(
                f"""
                <div style='display: flex; align-items: center; margin-bottom: 5px;'>
                    <span style='width: 20px; height: 20px; background-color: {status_color}; border-radius: 50%; display: inline-block; margin-right: 10px;'></span>
                    <span style='font-size: 1.5rem; font-weight: bold;'>{client_name}</span>
                </div>
                <div style='font-size: 0.9rem; color: #555;'>
                    <p>Date Last Updated: {previous_date if previous_date else 'N/A'}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Only show the dropdown to select new status and update button
            with col2:
                current_status_key = f"current_status_{client_id}"
                new_status = st.selectbox(
                    "Select New Status",
                    options=["", "Full Training", "Modified Training", "Rehab", "No Training"],
                    index=0,  # Keep dropdown empty initially
                    key=current_status_key
                )

                update_button_key = f"update_button_{client_id}"
                if st.button("Update", key=update_button_key):
                    if new_status:
                        # Save the new status and update the JSON
                        save_training_status_to_json(client_id, new_status, date.today(), previous_status, previous_date)
                        st.success(f"Status updated for {client_name} to {new_status}")

        # Divider between groups (instead of under the header)
        st.markdown("<hr>", unsafe_allow_html=True)


#-------------------------SETTINGS PAGE---------------------------------------
def render_settings_page(conn):
    # Load the icons
    settings_icon_path = Path(CONTENT_DIR) / 'settings.png'
    settings_icon_base64 = get_base64_image(settings_icon_path) if os.path.exists(settings_icon_path) else None

    logo_base64 = get_base64_image(LOGO_PATH) if os.path.exists(LOGO_PATH) else None

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center;">
                {'<img src="data:image/png;base64,' + settings_icon_base64 + '" style="width: 50px; margin-right: 10px;">' if settings_icon_base64 else ''}
                <h1 style='margin: 0;'>Settings</h1>
            </div>
            <div>
                {'<img src="data:image/png;base64,' + logo_base64 + '" style="width: 150px; float: right;">' if logo_base64 else ''}
            </div>
        </div>
        <hr style="margin-top: 10px;">
        """,
        unsafe_allow_html=True
    )

    # Add New User section header and clear button
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.write("### Add New User")
    with col2:
        if st.button('Clear', key="clear_add_user"):
            st.session_state["add_account_type"] = "Athlete"
            st.session_state["add_first_name"] = ""
            st.session_state["add_last_name"] = ""
            st.session_state["add_mobile"] = ""
            st.session_state["add_email"] = ""
            st.session_state["add_password"] = ""

    # Input fields for new user
    col1, col2, col3 = st.columns(3)
    account_type = col1.radio('Account Type', ['Athlete', 'Coach', 'Admin'], horizontal=True, key="add_account_type")
    first_name = col2.text_input('First Name', key="add_first_name")
    last_name = col3.text_input('Last Name', key="add_last_name")
    col4, col5, col6 = st.columns(3)
    mobile = col4.text_input('Mobile', key="add_mobile")
    email = col5.text_input('Email', key="add_email")
    password = col6.text_input('Password', type='password', key="add_password")

    # Generate and display client ID
    user_id = generate_client_id(conn)
    st.markdown(
        f"""
        <div style='text-align: right;'>
            Generated User ID: {user_id}
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Add User button and create folder
    col1, col2 = st.columns([0.85, 0.15])
    with col2:
        if st.button('Add User', key="add_user_button"):
            if not all([first_name, last_name, email, password]):
                st.error("First Name, Last Name, Email, and Password are required.")
            elif not email or "@" not in email or "." not in email:
                st.error("Please enter a valid email address.")
            elif not mobile.isdigit() or len(mobile) != 10 or not mobile.startswith("04"):
                st.error("Please enter a valid 10-digit mobile number starting with 04.")
            else:
                # Add the new user and create the folder
                folder_path = f'{PDF_DIR}/{last_name}_{first_name}_{user_id}'
                os.makedirs(folder_path, exist_ok=True)
                
                add_new_client(conn, user_id, account_type, first_name, last_name, mobile, email, password, 'active')
                st.success(f"User {first_name} {last_name} added successfully!")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Users List section header and clear button
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.write("### Users List")
    with col2:
        if st.button("Clear Filters", key="clear_filters"):
            st.session_state["search_name"] = ""
            st.session_state["filter_account_type"] = ""
            st.session_state["filter_status"] = ""

    # Filter options
    col1, col2, col3 = st.columns(3)
    search_name = col1.text_input("Search by name", key="search_name")
    filter_account_type = col2.selectbox("Filter by Account Type", [""] + ['Athlete', 'Coach', 'Admin'], key="filter_account_type")
    filter_status = col3.selectbox("Filter by Status", ["", "active", "deactivated"], key="filter_status")

    clients = fetch_all_clients(conn)

    filtered_clients = [
        client for client in clients
        if (st.session_state["search_name"].lower() in f"{client[3]}_{client[2]}".lower() if st.session_state["search_name"] else True) and
           (st.session_state["filter_account_type"] == client[1] if st.session_state["filter_account_type"] else True) and
           (st.session_state["filter_status"] == client[7] if st.session_state["filter_status"] else True)
    ]

    client_df = pd.DataFrame(filtered_clients, columns=["ID", "Account Type", "First Name", "Last Name", "Mobile", "Email", "Password", "Status"])
    st.dataframe(client_df, use_container_width=True)

    st.markdown("<div style='padding-bottom: 10px;'></div>", unsafe_allow_html=True)

    # Edit User Section
    st.write("### Edit User")
    dropdown_options = [""] + sorted([f"{client[3]}_{client[2]}_{client[0]}" for client in filtered_clients])
    selected_user = st.selectbox("Select User to Edit", dropdown_options, key="select_user_to_edit")

    if selected_user:
        selected_id = selected_user.split("_")[-1]
        selected_client = next(client for client in clients if client[0] == selected_id)

        col1, col2, col3, col4 = st.columns([0.3, 0.35, 0.35, 0.1])
        edit_account_type = col1.radio('Account Type', ['Athlete', 'Coach', 'Admin'], index=['Athlete', 'Coach', 'Admin'].index(selected_client[1]), horizontal=True, key="edit_account_type")
        edit_first_name = col2.text_input('First Name', value=selected_client[2], key="edit_first_name")
        edit_last_name = col3.text_input('Last Name', value=selected_client[3], key="edit_last_name")
        edit_status = col4.checkbox('Active', value=(selected_client[7] == 'active'), key="edit_status")
        col4.write("Status")

        col1, col2, col3 = st.columns(3)
        edit_mobile = col1.text_input('Mobile', value=selected_client[4], key="edit_mobile")
        edit_email = col2.text_input('Email', value=selected_client[5], key="edit_email")
        edit_password = col3.text_input('Password', value=selected_client[6], type='password', key="edit_password")

        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            if st.button('Update User', key="update_user_button"):
                if not all([edit_first_name, edit_last_name, edit_email, edit_password]):
                    st.error("First Name, Last Name, Email, and Password are required.")
                elif not edit_email or "@" not in edit_email or "." not in edit_email:
                    st.error("Please enter a valid email address.")
                elif not edit_mobile.isdigit() or len(edit_mobile) != 10 or not edit_mobile.startswith("04"):
                    st.error("Please enter a valid 10-digit mobile number starting with 04.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE clients
                        SET account_type = ?, first_name = ?, last_name = ?, mobile = ?, email = ?, password = ?, status = ?
                        WHERE id = ?
                    """, (edit_account_type, edit_first_name, edit_last_name, edit_mobile, edit_email, edit_password, 'active' if edit_status else 'deactivated', selected_id))
                    conn.commit()
                    st.success(f"User {edit_first_name} {edit_last_name} updated successfully!")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Add User Group Section
    st.write("### Add User Group")
    group_name = st.text_input("Group Name", key="add_group_name")

    # Format coaches with their ID
    coaches_with_ids = [f"{coach[0]} {coach[1]} (ID: {coach[2]})" for coach in fetch_coach_names_with_ids(conn)]
    selected_coaches = st.multiselect("Assign Coaches", coaches_with_ids)

    # Format athletes with their ID as well
    athletes_with_ids = [f"{athlete[0]} {athlete[1]} (ID: {athlete[2]})" for athlete in fetch_athlete_names_with_ids(conn)]
    selected_athletes = st.multiselect("Assign Athletes", athletes_with_ids)

    if st.button("Add User Group"):
        if not group_name.strip():
            st.error("Please provide a group name.")
        else:
            create_user_group(conn, group_name, selected_coaches, selected_athletes)
            st.success(f"User group '{group_name}' added successfully!")
            st.rerun()  # Refresh to reflect new data

    st.markdown("<hr>", unsafe_allow_html=True)

    # Fetch all user groups for display and editing
    groups_df = fetch_all_groups(conn)
    
    # Display Groups Table
    st.write("### Group List")
    st.dataframe(groups_df, use_container_width=True)

    # Edit User Group Section
    st.write("### Edit User Group")
    group_options = [""] + sorted([f"{row['Group ID']} - {row['Group Name']}" for index, row in groups_df.iterrows()])
    selected_group = st.selectbox("Select User Group to Edit", options=group_options, key="select_group_to_edit")

    if selected_group:
        group_id = selected_group.split(" - ")[0]
        selected_group_info = groups_df[groups_df["Group ID"] == int(group_id)].iloc[0]

        edit_group_name = st.text_input("Group Name", value=selected_group_info["Group Name"], key="edit_group_name")

        # Safeguard against empty or None coach field
        coaches = selected_group_info["Coaches"] if selected_group_info["Coaches"] else ""
        valid_coaches = [coach for coach in coaches_with_ids if coach.split(" (ID: ")[0] in coaches.split(', ')]
        edit_selected_coaches = st.multiselect("Assign Coaches", coaches_with_ids, default=valid_coaches)

        # Safeguard against empty or None athlete field
        athletes = selected_group_info["Clients"] if selected_group_info["Clients"] else ""
        valid_athletes = [athlete for athlete in athletes_with_ids if athlete.split(" (ID: ")[0] in athletes.split(', ')]
        edit_selected_athletes = st.multiselect("Assign Athletes", athletes_with_ids, default=valid_athletes)

        # Button to update the group
        if st.button("Update User Group"):
            if not edit_group_name.strip():
                st.error("Please provide a group name.")
            else:
                # Update group information
                update_user_group(conn, group_id, edit_group_name, edit_selected_coaches, edit_selected_athletes)
                st.success(f"User group '{edit_group_name}' updated successfully!")
                st.rerun()  # Refresh to reflect changes


#-----------------Main function to manage the app-------------------------------
def main():
    set_custom_theme()
    initialize_session_state()

    # Initialize SQLite database
    conn = sqlite3.connect(CLIENT_DB_PATH)
    initialize_database()  # Creates the clients table

    manage_sidebar()

    # Menu navigation
    if st.session_state.menu_choice == "Home":
        display_home_page()
    elif st.session_state.menu_choice == "New Program":
        data = load_data()
        render_new_prescription_page(data, conn)
    elif st.session_state.menu_choice == "Modify Program":
        data = load_data()
        existing_patients = load_existing_patients()
        render_modify_prescription_page(data, existing_patients)
    elif st.session_state.menu_choice == "Client Status":
        render_client_status_page(conn)  # Pass the database connection directly
    elif st.session_state.menu_choice == "Client History":
        existing_patients = load_existing_patients()
        render_client_history_page(existing_patients)
    elif st.session_state.menu_choice == "Exercise Database":
        data = load_data()
        render_exercise_database_page(data)
    elif st.session_state.menu_choice == "Settings":
        render_settings_page(conn)

    conn.close()

# This ensures that the app runs when you execute the script directly
if __name__ == "__main__":
    main()

