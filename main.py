import streamlit as st
import pandas as pd
#from PIL import Image
from fpdf import FPDF
from datetime import date, timedelta
import os
import json
#import numpy as np

# Constants
LOGO_PATH = 'images/company_logo.png'
PDF_DIR = 'patient_pdfs'
EXERCISE_IMG_DIR = 'exercise_images'

# Set wide mode and custom theme
def set_custom_theme():
    st.set_page_config(layout="wide", page_title="Exercise Prescription", page_icon=":muscle:")
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
            background-color: var(--primary-color);
            border: 1px solid var(--primary-color);
        }
        .stButton>button:active {
            background-color: var(--primary-color);
            border: 1px solid var(--primary-color);
        }
        .stButton>button.selected {
            background-color: var(--primary-color);
            color: #ffffff;
            border: 1px solid var(--primary-color);
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

# Load data
def load_data():
    data = pd.read_csv('exercise_database.csv')
    if 'body_part' not in data.columns:
        st.error("The 'body_part' column is missing from the CSV file. Please check the CSV file.")
        st.stop()
    return data

# Initialize session state
def initialize_session_state():
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

# Utility functions
def add_exercise():
    st.session_state.exercises.append(len(st.session_state.exercises))

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

def save_pdf(pdf, lastname, firstname, rehab_type, prescription_date, selected_exercises, extra_comments):
    folder_name = f"{lastname}_{firstname}"
    folder_path = os.path.join('patient_pdfs', folder_name)
    os.makedirs(folder_path, exist_ok=True)
    details_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.json"
    details_file_path = os.path.join(folder_path, details_file_name)
    
    # Save PDF to desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    pdf_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.pdf"
    pdf_file_path = os.path.join(desktop_path, pdf_file_name)
    
    # Check and remove trailing spaces in the file path
    pdf_file_path = pdf_file_path.strip()

    pdf.output(pdf_file_path)
    
    # Save prescription details in a JSON file
    prescription_details = {
        'firstname': firstname,
        'lastname': lastname,
        'rehab_type': rehab_type,
        'prescription_date': str(prescription_date),
        'exercises': selected_exercises,
        'extra_comments': extra_comments
    }
    with open(details_file_path, 'w') as details_file:
        json.dump(prescription_details, details_file)
    
    return pdf_file_path

def load_existing_patients():
    patients = {}
    if os.path.exists(PDF_DIR):
        for folder in os.listdir(PDF_DIR):
            patient_name = folder
            json_files = [f for f in os.listdir(os.path.join(PDF_DIR, folder)) if f.endswith('.json')]
            patients[patient_name] = json_files
    return patients

def load_prescription(selected_json):
    patient_name, json_file = selected_json.split("/")
    with open(os.path.join(PDF_DIR, patient_name, json_file), 'r') as details_file:
        prescription_details = json.load(details_file)
    
    st.session_state['first_name'] = prescription_details['firstname']
    st.session_state['last_name'] = prescription_details['lastname']
    st.session_state['rehab_type'] = prescription_details['rehab_type']
    st.session_state['prescription_date'] = date.fromisoformat(prescription_details['prescription_date'])
    st.session_state.exercises = list(range(len(prescription_details['exercises'])))
    st.session_state['extra_comments'] = prescription_details['extra_comments']
    
    for i, exercise in enumerate(prescription_details['exercises']):
        st.session_state[f'body_part_{i}'] = exercise['body_part']
        st.session_state[f'movement_type_{i}'] = exercise['movement_type']
        st.session_state[f'sub_movement_type_{i}'] = exercise['sub_movement_type']
        st.session_state[f'exercise_{i}'] = exercise['exercise']
        st.session_state[f'notes_{i}'] = exercise['notes']
        st.session_state[f'volume_{i}'] = exercise['volume']
    
    st.experimental_rerun()

def create_sidebar():
    st.sidebar.image(LOGO_PATH, use_column_width=True)

    menu_options = ["New Prescription", "Modify Prescription", "Client History", "Exercise Database"]
    if 'menu_choice' not in st.session_state:
        st.session_state['menu_choice'] = "New Prescription"

    def set_menu_choice(choice):
        if choice == "New Prescription":
            reset_session_state()
        st.session_state['menu_choice'] = choice

    for option in menu_options:
        if st.sidebar.button(option):
            set_menu_choice(option)

    return st.session_state['menu_choice']

def render_exercise_fields(data):
    selected_exercises = []
    for i in st.session_state.exercises:
        cols1 = st.columns([0.25, 0.75, 0.75, 0.75, 2])
        cols1[0].write(f"{i+1}.")
        body_part = cols1[1].selectbox(f'Body Part {i+1}', [""] + list(data['body_part'].unique()), key=f'body_part_{i}', index=0)
        
        movement_data = data[data['body_part'] == body_part] if body_part else pd.DataFrame(columns=['movement_type'])
        movement_type = cols1[2].selectbox(f'Movement Type {i+1}', [""] + list(movement_data['movement_type'].unique()), key=f'movement_type_{i}', index=0)
        
        sub_movement_data = movement_data[movement_data['movement_type'] == movement_type] if movement_type else pd.DataFrame(columns=['sub_movement_type'])
        sub_movement_type = cols1[3].selectbox(f'Sub Movement Type {i+1}', [""] + list(sub_movement_data['sub_movement_type'].unique()), key=f'sub_movement_type_{i}', index=0)
        
        exercise_data = sub_movement_data[sub_movement_data['sub_movement_type'] == sub_movement_type] if sub_movement_type else pd.DataFrame(columns=['exercise'])
        exercise = cols1[4].selectbox(f'Exercise {i+1}', [""] + list(exercise_data['exercise'].unique()), key=f'exercise_{i}', index=0)
        
        cols2 = st.columns([0.25, 1.65, 3])
        volume = cols2[1].text_input(f'Volume {i+1}', key=f'volume_{i}', value="" if exercise_data[exercise_data['exercise'] == exercise].empty else exercise_data[exercise_data['exercise'] == exercise].iloc[0]['volume'])
        notes = cols2[2].text_input(f'Notes {i+1}', key=f'notes_{i}', value="")
        
        selected_exercises.append({
            'body_part': body_part,
            'movement_type': movement_type,
            'sub_movement_type': sub_movement_type,
            'exercise': exercise,
            'volume': volume,
            'notes': notes
        })
    return selected_exercises

def generate_pdf(pdf, selected_exercises):
    # Add logo
    pdf.image(LOGO_PATH, 10, 8, 33)
    
    # Add header text
    pdf.set_font("Arial", size=12)
    pdf.set_xy(150, 10)
    pdf.multi_cell(50, 10, "Catherine King\nSports Physiotherapist\n0438503185", align='R')
    
    pdf.set_xy(10, 50)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=st.session_state['rehab_type'], ln=True, align='L')
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 5, txt=f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}", ln=True, align='L')
    pdf.cell(200, 5, txt=f"Prescription Date: {st.session_state['prescription_date']}", ln=True, align='L')
    
    # Add a line
    pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
    pdf.ln(10)

    pdf.set_font("Arial", size=10)
    for movement_type in set(ex['movement_type'] for ex in selected_exercises):
        # Add a line before each movement type
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=movement_type, ln=True)
        pdf.set_font("Arial", size=10)
        
        for exercise in selected_exercises:
            if exercise['movement_type'] == movement_type:
                text = f"{exercise['exercise']}\nBody Part: {exercise['body_part']}\nVolume: {exercise['volume']}\nNotes: {exercise['notes']}"
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
                
                pdf.ln(5)  # Add space between exercises
                        
    # Add a line before extra comments
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Add extra comments
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Extra Comments", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=st.session_state['extra_comments'], align='L')

def render_new_prescription_page(data):
    # App title and description
    st.title('Exercise Prescription')
    
    # Patient details
    col1, col2, col3 = st.columns([1, 1, 1])
    first_name = col1.text_input('First Name', key='first_name')
    last_name = col2.text_input('Last Name', key='last_name')

    col4, col5 = st.columns([2, 1])
    rehab_type = col4.text_input('Rehab Type', key='rehab_type')
    prescription_date = col5.date_input('Prescription Date', value=date.today(), key='prescription_date')

    # Exercises heading
    st.write("### Exercises")

    # Button to add new exercise
    st.button('Add Exercise', on_click=add_exercise, key='add_exercise', help='Add Exercise')

    # Create dropdowns for exercises
    selected_exercises = render_exercise_fields(data)

    # Collect extra comments or notes
    extra_comments = st.text_area('Extra Comments or Notes', key='extra_comments')

    # Increase the text size of the 'Extra Comments or Notes' text area
    st.markdown("""
        <style>
        .stTextArea textarea {
            font-size: 1.2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Export button is enabled only if first name, last name, rehab type, and date are filled in
    if st.session_state['first_name'] and st.session_state['last_name'] and st.session_state['rehab_type'] and st.session_state['prescription_date']:
        export_button = st.button('Export to PDF', key='export_button', help='Export to PDF')
    else:
        export_button = st.button('Export to PDF', disabled=True, key='export_button', help='Name and rehab type must be entered before exporting')

    # Preview section
    render_preview_section(selected_exercises)

    # Export to PDF
    if export_button:
        pdf = FPDF()
        pdf.add_page()
        generate_pdf(pdf, selected_exercises)
        
        # Save PDF and prescription details
        file_path = save_pdf(pdf, st.session_state['last_name'], st.session_state['first_name'], st.session_state['rehab_type'], st.session_state['prescription_date'], selected_exercises, st.session_state['extra_comments'])
        st.success(f'PDF generated and saved to {file_path}')
    
def render_modify_prescription_page(data, existing_patients):
    # App title and description
    st.title('Modify Prescription')
    
    # Recall Sent PDF section
    st.write("### Recall Sent PDF")
    patient_name = st.selectbox('Select Patient', options=[""] + list(existing_patients.keys()))
    if patient_name:
        json_files = existing_patients.get(patient_name, [])
        selected_json = st.selectbox('Select Prescription', options=[""] + [f"{patient_name}/{json_file}" for json_file in json_files])
        if selected_json and st.button('Load Prescription'):
            load_prescription(selected_json)

    # Patient details
    col1, col2, col3 = st.columns([1, 1, 1])
    first_name = col1.text_input('First Name', key='first_name')
    last_name = col2.text_input('Last Name', key='last_name')

    col4, col5 = st.columns([2, 1])
    rehab_type = col4.text_input('Rehab Type', key='rehab_type')
    prescription_date = col5.date_input('Prescription Date', value=date.today(), key='prescription_date')

    # Exercises heading
    st.write("### Exercises")

    # Button to add new exercise
    st.button('Add Exercise', on_click=add_exercise, key='add_exercise_modify', help='Add Exercise')

    # Create dropdowns for exercises
    selected_exercises = render_exercise_fields(data)

    # Collect extra comments or notes
    extra_comments = st.text_area('Extra Comments or Notes', key='extra_comments')

    # Increase the text size of the 'Extra Comments or Notes' text area
    st.markdown("""
        <style>
        .stTextArea textarea {
            font-size: 1.2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Export button is enabled only if first name, last name, rehab type, and date are filled in
    if st.session_state['first_name'] and st.session_state['last_name'] and st.session_state['rehab_type'] and st.session_state['prescription_date']:
        export_button = st.button('Export to PDF', key='export_button_modify', help='Export to PDF')
    else:
        export_button = st.button('Export to PDF', disabled=True, key='export_button_modify', help='Name and rehab type must be entered before exporting')

    # Preview section
    render_preview_section(selected_exercises)

    # Export to PDF
    if export_button:
        pdf = FPDF()
        pdf.add_page()
        generate_pdf(pdf, selected_exercises)
        
        # Save PDF and prescription details
        file_path = save_pdf(pdf, st.session_state['last_name'], st.session_state['first_name'], st.session_state['rehab_type'], st.session_state['prescription_date'], selected_exercises, st.session_state['extra_comments'])
        st.success(f'PDF generated and saved to {file_path}')
    
def render_preview_section(selected_exercises):
    with st.expander("Preview Program PDF", expanded=False):
        # Header
        st.image(LOGO_PATH, width=100)
        st.write(f"<h2>{st.session_state['rehab_type']}</h2>", unsafe_allow_html=True)
        st.write(f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}")
        st.write(f"Prescription Date: {st.session_state['prescription_date']}")

        # Exercises
        for movement_type in set(ex['movement_type'] for ex in selected_exercises):
            st.write(f"### {movement_type}")
            for exercise in selected_exercises:
                if exercise['movement_type'] == movement_type:
                    st.write(f"**{exercise['exercise']}**")
                    st.write(f"Body Part: {exercise['body_part']}")
                    st.write(f"Volume: {exercise['volume']}")
                    st.write(f"Notes: {exercise['notes']}")
                    
                    image_path_jpg = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.jpg"
                    image_path_png = f"{EXERCISE_IMG_DIR}/{exercise['exercise']}.png"
                    image_path = None
                    
                    if os.path.exists(image_path_jpg):
                        image_path = image_path_jpg
                    elif os.path.exists(image_path_png):
                        image_path = image_path_png
                    
                    if image_path:
                        st.image(image_path, width=100)
        
        # Extra comments
        st.write("### Extra Comments")
        st.write(st.session_state['extra_comments'])

def render_client_history_page(existing_patients):
    st.title('Client History')
    
    # Instructions for filtering
    st.write('<span style="color: grey;">Use the dropdowns below to filter the table displayed.</span>', unsafe_allow_html=True)

    # Filter for client name and date range
    col1, col2, col3 = st.columns([2, 1, 1])
    client_filter = col1.selectbox('Client Name', options=[""] + list(existing_patients.keys()))
    start_date = col2.date_input('Start Date', value=date.today() - timedelta(days=6*30))
    end_date = col3.date_input('End Date', value=date.today())

    # Collect all prescriptions
    all_prescriptions = []
    for patient_name, files in existing_patients.items():
        for file in files:
            with open(os.path.join(PDF_DIR, patient_name, file), 'r') as details_file:
                prescription_details = json.load(details_file)
                prescription_details['file_name'] = file
                prescription_details['patient_name'] = patient_name
                all_prescriptions.append(prescription_details)
    
    # Create DataFrame and filter if needed
    df = pd.DataFrame(all_prescriptions)
    if client_filter:
        df = df[df['patient_name'] == client_filter]
    
    df = df[(df['prescription_date'] >= str(start_date)) & (df['prescription_date'] <= str(end_date))]
    df = df.sort_values(by='prescription_date', ascending=False)
    
    # Rename and reorder columns
    df = df.rename(columns={
        'prescription_date': 'Date',
        'patient_name': 'Client Name',
        'rehab_type': 'Rehab Type',
        'exercises': 'Exercises'
    })[['Date', 'Client Name', 'Rehab Type', 'Exercises']]

    # Format exercises by movement type
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
    
    # Adjust column widths
    st.write(f"<style>div[data-testid='stDataFrame'] th:nth-child(1), div[data-testid='stDataFrame'] td:nth-child(1) {{width: 50px !important;}} div[data-testid='stDataFrame'] th:nth-child(2), div[data-testid='stDataFrame'] td:nth-child(2) {{width: 100px !important;}}</style>", unsafe_allow_html=True)
    
    # Display the count of programs
    st.write(f"Total Programs: {len(df)}")
    
    # Display the filtered prescriptions
    st.dataframe(df, use_container_width=True)

def render_exercise_database_page(data):
    st.title('Exercise Database')

    # Instructions for filtering
    st.write('<span style="color: grey;">Adding filters from the dropdowns will reduce the exercises displayed in the table to assist you in finding what you\'re looking for.</span>', unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)
    body_part_filter = col1.selectbox('Body Part', [""] + list(data['body_part'].unique()))
    movement_type_filter = col2.selectbox('Movement Type', [""] + list(data[data['body_part'] == body_part_filter]['movement_type'].unique()) if body_part_filter else [""])
    sub_movement_type_filter = col3.selectbox('Sub Movement Type', [""] + list(data[(data['body_part'] == body_part_filter) & (data['movement_type'] == movement_type_filter)]['sub_movement_type'].unique()) if body_part_filter and movement_type_filter else [""])

    # Select exercise to edit dropdown and its instructions
    st.write('<span style="color: grey;">Find the exercise to edit from the dropdown. The associated fields to that exercise can then be modified. Ensure you press save changes at the end.</span>', unsafe_allow_html=True)
    edit_exercise_options = [f"{row['body_part']} - {row['movement_type']} - {row['sub_movement_type']} - {row['exercise']}" for idx, row in data.iterrows()]
    edit_exercise_index = st.selectbox("Select Exercise to Edit", options=[""] + edit_exercise_options)
    
    if edit_exercise_index:
        selected_exercise = data.iloc[edit_exercise_options.index(edit_exercise_index) - 1]
        st.write(f"Editing Exercise: {selected_exercise['exercise']}")
        with st.form(key=f'edit_form_{edit_exercise_index}'):
            body_part_edit = st.selectbox('Body Part', list(data['body_part'].unique()), index=list(data['body_part'].unique()).index(selected_exercise['body_part']))
            movement_type_edit = st.selectbox('Movement Type', list(data[data['body_part'] == body_part_edit]['movement_type'].unique()), index=list(data[data['body_part'] == body_part_edit]['movement_type'].unique()).index(selected_exercise['movement_type']))
            sub_movement_type_edit = st.selectbox('Movement Sub-Type', list(data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()), index=list(data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()).index(selected_exercise['sub_movement_type']))
            exercise_edit = st.text_input('Exercise', value=selected_exercise['exercise'])
            volume_edit = st.text_input('Volume', value="" if pd.isna(selected_exercise['volume']) else selected_exercise['volume'])
            notes_edit = st.text_area('Notes', value="" if pd.isna(selected_exercise['notes']) else selected_exercise['notes'])
            
            # Upload image
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png"])
            if uploaded_file:
                image_path = f"{EXERCISE_IMG_DIR}/{exercise_edit}.{uploaded_file.name.split('.')[-1]}"
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"Uploaded {uploaded_file.name} for exercise {exercise_edit}")
            
            # Display current image and delete option
            image_path_jpg = f"{EXERCISE_IMG_DIR}/{selected_exercise['exercise']}.jpg"
            image_path_png = f"{EXERCISE_IMG_DIR}/{selected_exercise['exercise']}.png"
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
                    st.success(f"Deleted image for exercise {selected_exercise['exercise']}")
            
            save_changes = st.form_submit_button('Save Changes')
            if save_changes:
                data.loc[selected_exercise.name, 'body_part'] = body_part_edit
                data.loc[selected_exercise.name, 'movement_type'] = movement_type_edit
                data.loc[selected_exercise.name, 'sub_movement_type'] = sub_movement_type_edit
                data.loc[selected_exercise.name, 'exercise'] = exercise_edit
                data.loc[selected_exercise.name, 'volume'] = volume_edit
                data.loc[selected_exercise.name, 'notes'] = notes_edit
                data.to_csv('exercise_database.csv', index=False)
                st.success('Exercise updated successfully!')
                st.experimental_rerun()

    if body_part_filter or movement_type_filter or sub_movement_type_filter:
        filtered_data = data[
            (data['body_part'] == body_part_filter if body_part_filter else True) &
            (data['movement_type'] == movement_type_filter if movement_type_filter else True) &
            (data['sub_movement_type'] == sub_movement_type_filter if sub_movement_type_filter else True)
        ]
    else:
        filtered_data = data

    # Rename columns
    filtered_data = filtered_data.rename(columns={
        'body_part': 'Body Part',
        'movement_type': 'Movement Type',
        'sub_movement_type': 'Movement Sub-Type',
        'exercise': 'Exercise',
        'volume': 'Volume',
        'notes': 'Notes'
    })

    # Replace NaN values with empty strings
    filtered_data = filtered_data.fillna('')

    # Add column for image file names
    def get_image_name(exercise):
        image_jpg = f"{EXERCISE_IMG_DIR}/{exercise}.jpg"
        image_png = f"{EXERCISE_IMG_DIR}/{exercise}.png"
        if os.path.exists(image_jpg) or os.path.exists(image_png):
            return exercise
        else:
            return "No Image"

    filtered_data['Image'] = filtered_data['Exercise'].apply(get_image_name)
    
    # Displaying the custom exercise list
    st.write("### Custom Exercise List")
    
    st.dataframe(filtered_data, use_container_width=True)

def main():
    set_custom_theme()
    data = load_data()
    initialize_session_state()
    menu_choice = create_sidebar()
    existing_patients = load_existing_patients()

    if menu_choice == "New Prescription":
        render_new_prescription_page(data)
    elif menu_choice == "Modify Prescription":
        render_modify_prescription_page(data, existing_patients)
    elif menu_choice == "Client History":
        render_client_history_page(existing_patients)
    elif menu_choice == "Exercise Database":
        render_exercise_database_page(data)

if __name__ == "__main__":
    main()
