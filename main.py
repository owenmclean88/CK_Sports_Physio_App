import streamlit as st
import pandas as pd
from PIL import Image
from fpdf import FPDF
from datetime import date, timedelta
import os
import json
import numpy as np

# Set wide mode
st.set_page_config(layout="wide")

# Load your data
data = pd.read_csv('exercise_database.csv')

# Initialize session state for exercises and prescription type
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

# Function to add a new exercise
def add_exercise():
    st.session_state.exercises.append(len(st.session_state.exercises))

# Function to reset session state for a new prescription
def reset_session_state():
    st.session_state.exercises = [0]
    st.session_state.first_name = ''
    st.session_state.last_name = ''
    st.session_state.rehab_type = ''
    st.session_state.extra_comments = ''
    for key in list(st.session_state.keys()):
        if key.startswith('body_part_') or key.startswith('movement_type_') or key.startswith('sub_movement_type_') or key.startswith('exercise_') or key.startswith('notes_') or key.startswith('volume_'):
            del st.session_state[key]

# Function to save PDF and prescription details in the correct folder structure
def save_pdf(pdf, lastname, firstname, rehab_type, prescription_date, selected_exercises, extra_comments):
    folder_name = f"{lastname}_{firstname}"
    folder_path = os.path.join('patient_pdfs', folder_name)
    os.makedirs(folder_path, exist_ok=True)
    details_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.json"
    details_file_path = os.path.join(folder_path, details_file_name)
    
    # Save PDF to desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    pdf_folder = os.path.join(desktop_path, folder_name)
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_file_name = f"{lastname}_{firstname}_{rehab_type}_{prescription_date}.pdf"
    pdf_file_path = os.path.join(pdf_folder, pdf_file_name)
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

# Function to load existing patients and their prescription details
def load_existing_patients():
    patients = {}
    if os.path.exists('patient_pdfs'):
        for folder in os.listdir('patient_pdfs'):
            patient_name = folder
            json_files = [f for f in os.listdir(os.path.join('patient_pdfs', folder)) if f.endswith('.json')]
            patients[patient_name] = json_files
    return patients

# Load existing patients
existing_patients = load_existing_patients()

# Callback function to load prescription
def load_prescription(selected_json):
    patient_name, json_file = selected_json.split("/")
    with open(os.path.join('patient_pdfs', patient_name, json_file), 'r') as details_file:
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

# Sidebar menu
st.sidebar.image('images/company_logo.png', use_column_width=True)

menu_options = ["New Prescription", "Modify Prescription", "Client History", "Exercise Database"]
if 'menu_choice' not in st.session_state:
    st.session_state['menu_choice'] = "New Prescription"

# Function to set menu choice and reset session state if switching to new prescription
def set_menu_choice(choice):
    if choice == "New Prescription":
        reset_session_state()
    st.session_state['menu_choice'] = choice

for option in menu_options:
    if st.sidebar.button(option):
        set_menu_choice(option)

menu_choice = st.session_state['menu_choice']

def render_exercise_fields():
    selected_exercises = []
    for i in st.session_state.exercises:
        cols = st.columns([0.5, 1, 1, 1, 1, 1, 1, 2])  # Adjusted columns
        cols[0].write(f"{i+1}.")
        body_part = cols[1].selectbox(f'Body Part {i+1}', [""] + list(data['body_part'].unique()), key=f'body_part_{i}', index=0)
        
        movement_data = data[data['body_part'] == body_part] if body_part else pd.DataFrame(columns=['movement_type'])
        movement_type = cols[2].selectbox(f'Movement Type {i+1}', [""] + list(movement_data['movement_type'].unique()), key=f'movement_type_{i}', index=0)
        
        sub_movement_data = movement_data[movement_data['movement_type'] == movement_type] if movement_type else pd.DataFrame(columns=['sub_movement_type'])
        sub_movement_type = cols[3].selectbox(f'Sub Movement Type {i+1}', [""] + list(sub_movement_data['sub_movement_type'].unique()), key=f'sub_movement_type_{i}', index=0)
        
        exercise_data = sub_movement_data[sub_movement_data['sub_movement_type'] == sub_movement_type] if sub_movement_type else pd.DataFrame(columns=['exercise'])
        exercise = cols[4].selectbox(f'Exercise {i+1}', [""] + list(exercise_data['exercise'].unique()), key=f'exercise_{i}', index=0)
        
        volume = cols[5].text_input(f'Volume {i+1}', key=f'volume_{i}', value="" if exercise_data[exercise_data['exercise'] == exercise].empty else exercise_data[exercise_data['exercise'] == exercise].iloc[0]['volume'])
        
        notes = cols[7].text_input(f'Notes {i+1}', key=f'notes_{i}', value="")
        
        # Display exercise image
        image_col = cols[6]
        if exercise:
            image_path_jpg = f"exercise_images/{exercise}.jpg"
            image_path_png = f"exercise_images/{exercise}.png"
            image_path = None
            
            if os.path.exists(image_path_jpg):
                image_path = image_path_jpg
            elif os.path.exists(image_path_png):
                image_path = image_path_png
            
            if image_path:
                image_col.image(image_path, use_column_width=True)
            else:
                image_col.write(f"Image not found for {exercise}")
                st.write(f"Debug: Image not found at {image_path_jpg} or {image_path_png}")
        
        selected_exercises.append({
            'body_part': body_part,
            'movement_type': movement_type,
            'sub_movement_type': sub_movement_type,
            'exercise': exercise,
            'volume': volume,
            'notes': notes
        })
    return selected_exercises

if menu_choice == "New Prescription":
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
    selected_exercises = render_exercise_fields()

    # Collect extra comments or notes
    extra_comments = st.text_area('Extra Comments or Notes', key='extra_comments')

    # Export button is enabled only if first name, last name, rehab type, and date are filled in
    if st.session_state['first_name'] and st.session_state['last_name'] and st.session_state['rehab_type'] and st.session_state['prescription_date']:
        export_button = st.button('Export to PDF', key='export_button', help='Export to PDF')
    else:
        export_button = st.button('Export to PDF', disabled=True, key='export_button', help='Name and rehab type must be entered before exporting')

    # Export to PDF
    if export_button:
        pdf = FPDF()
        pdf.add_page()
        
        # Add company logo
        pdf.image('images/company_logo.png', 10, 8, 33)
        
        # Add patient details
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}", ln=True)
        pdf.cell(200, 10, txt=f"Rehab Type: {st.session_state['rehab_type']}", ln=True)
        pdf.cell(200, 10, txt=f"Prescription Date: {st.session_state['prescription_date']}", ln=True)
        
        # Add exercises
        pdf.set_font("Arial", size=10)
        for i, exercise in enumerate(selected_exercises):
            pdf.cell(200, 10, txt=f"{i+1}. Exercise: {exercise['exercise']}", ln=True)
            pdf.cell(200, 10, txt=f"Volume: {exercise['volume']}", ln=True)
            pdf.cell(200, 10, txt=f"Notes: {exercise['notes']}", ln=True)
            pdf.cell(200, 10, txt=f"Comments: {st.session_state['extra_comments']}", ln=True)
            pdf.ln(10)
        
        # Save PDF and prescription details
        file_path = save_pdf(pdf, st.session_state['last_name'], st.session_state['first_name'], st.session_state['rehab_type'], st.session_state['prescription_date'], selected_exercises, st.session_state['extra_comments'])
        st.success(f'PDF generated and saved to {file_path}')

elif menu_choice == "Modify Prescription":
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
    selected_exercises = render_exercise_fields()

    # Collect extra comments or notes
    extra_comments = st.text_area('Extra Comments or Notes', key='extra_comments')

    # Export button is enabled only if first name, last name, rehab type, and date are filled in
    if st.session_state['first_name'] and st.session_state['last_name'] and st.session_state['rehab_type'] and st.session_state['prescription_date']:
        export_button = st.button('Export to PDF', key='export_button_modify', help='Export to PDF')
    else:
        export_button = st.button('Export to PDF', disabled=True, key='export_button_modify', help='Name and rehab type must be entered before exporting')

    # Export to PDF
    if export_button:
        pdf = FPDF()
        pdf.add_page()
        
        # Add company logo
        pdf.image('images/company_logo.png', 10, 8, 33)
        
        # Add patient details
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Patient Name: {st.session_state['first_name']} {st.session_state['last_name']}", ln=True)
        pdf.cell(200, 10, txt=f"Rehab Type: {st.session_state['rehab_type']}", ln=True)
        pdf.cell(200, 10, txt=f"Prescription Date: {st.session_state['prescription_date']}", ln=True)
        
        # Add exercises
        pdf.set_font("Arial", size=10)
        for i, exercise in enumerate(selected_exercises):
            pdf.cell(200, 10, txt=f"{i+1}. Exercise: {exercise['exercise']}", ln=True)
            pdf.cell(200, 10, txt=f"Volume: {exercise['volume']}", ln=True)
            pdf.cell(200, 10, txt=f"Notes: {exercise['notes']}", ln=True)
            pdf.cell(200, 10, txt=f"Comments: {st.session_state['extra_comments']}", ln=True)
            pdf.ln(10)
        
        # Save PDF and prescription details
        file_path = save_pdf(pdf, st.session_state['last_name'], st.session_state['first_name'], st.session_state['rehab_type'], st.session_state['prescription_date'], selected_exercises, st.session_state['extra_comments'])
        st.success(f'PDF generated and saved to {file_path}')

elif menu_choice == "Client History":
    st.title('Client History')
    
    # Instructions for filtering
    st.write('<span style="color: grey;">Use the dropdowns below to filter the table displayed.</span>', unsafe_allow_html=True)

    # Filter for client name and date range
    col1, col2, col3 = st.columns([3, 1, 1])
    client_filter = col1.selectbox('Client Name', options=[""] + list(existing_patients.keys()))
    start_date = col2.date_input('Start Date', value=date.today() - timedelta(days=6*30))
    end_date = col3.date_input('End Date', value=date.today())

    # Collect all prescriptions
    all_prescriptions = []
    for patient_name, files in existing_patients.items():
        for file in files:
            with open(os.path.join('patient_pdfs', patient_name, file), 'r') as details_file:
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
            formatted += f"**{movement_type}**\n"
            for ex in exercises:
                formatted += f"- {ex}\n"
        return formatted

    df['Exercises'] = df['Exercises'].apply(format_exercises)
    
    # Adjust column widths
    st.write(f"<style>div[data-testid='stDataFrame'] th:nth-child(1), div[data-testid='stDataFrame'] td:nth-child(1) {{width: 50px !important;}} div[data-testid='stDataFrame'] th:nth-child(2), div[data-testid='stDataFrame'] td:nth-child(2) {{width: 100px !important;}}</style>", unsafe_allow_html=True)
    
    # Display the count of programs
    st.write(f"Total Programs: {len(df)}")
    
    # Display the filtered prescriptions
    st.dataframe(df, use_container_width=True)

elif menu_choice == "Exercise Database":
    st.title('Exercise Database')

    # Instructions for filtering
    st.write('<span style="color: grey;">Adding filters from the dropdowns will reduce the exercises displayed in the table to assist you in finding what you\'re looking for.</span>', unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns(3)
    body_part_filter = col1.selectbox('Body Part', [""] + list(data['body_part'].unique()))
    movement_type_filter = col2.selectbox('Movement Type', [""] + list(data[data['body_part'] == body_part_filter]['movement_type'].unique()) if body_part_filter else [""])
    sub_movement_type_filter = col3.selectbox('Sub Movement Type', [""] + list(data[(data['body_part'] == body_part_filter) & (data['movement_type'] == movement_type_filter)]['sub_movement_type'].unique()) if body_part_filter and movement_type_filter else [""])

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

    # Add column for image file names
    def get_image_name(exercise):
        image_jpg = f"exercise_images/{exercise}.jpg"
        image_png = f"exercise_images/{exercise}.png"
        if os.path.exists(image_jpg):
            return f"{exercise}.jpg"
        elif os.path.exists(image_png):
            return f"{exercise}.png"
        else:
            return "No Image"

    filtered_data['Image'] = filtered_data['Exercise'].apply(get_image_name)
    
    st.dataframe(filtered_data, use_container_width=True)

    # Instructions for editing exercises
    st.write('<span style="color: grey;">Find the exercise to edit from the dropdown. The associated fields to that exercise can then be modified. Ensure you press save changes at the end.</span>', unsafe_allow_html=True)

    # Editing Exercises
    if not filtered_data.empty:
        edit_exercise_options = [f"{row['Body Part']} - {row['Movement Type']} - {row['Movement Sub-Type']} - {row['Exercise']}" for idx, row in filtered_data.iterrows()]
        edit_exercise_index = st.selectbox("Select Exercise to Edit", options=[""] + edit_exercise_options)
        
        if edit_exercise_index:
            selected_exercise = filtered_data.iloc[edit_exercise_options.index(edit_exercise_index)]
            st.write(f"Editing Exercise: {selected_exercise['Exercise']}")
            with st.form(key=f'edit_form_{edit_exercise_index}'):
                body_part_edit = st.selectbox('Body Part', list(data['body_part'].unique()), index=list(data['body_part'].unique()).index(selected_exercise['Body Part']))
                movement_type_edit = st.selectbox('Movement Type', list(data[data['body_part'] == body_part_edit]['movement_type'].unique()), index=list(data[data['body_part'] == body_part_edit]['movement_type'].unique()).index(selected_exercise['Movement Type']))
                sub_movement_type_edit = st.selectbox('Movement Sub-Type', list(data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()), index=list(data[(data['body_part'] == body_part_edit) & (data['movement_type'] == movement_type_edit)]['sub_movement_type'].unique()).index(selected_exercise['Movement Sub-Type']))
                exercise_edit = st.text_input('Exercise', value=selected_exercise['Exercise'])
                volume_edit = st.text_input('Volume', value="" if pd.isna(selected_exercise['Volume']) else selected_exercise['Volume'])
                notes_edit = st.text_area('Notes', value="" if pd.isna(selected_exercise['Notes']) else selected_exercise['Notes'])
                
                # Upload image
                uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png"])
                if uploaded_file:
                    image_path = f"exercise_images/{exercise_edit}.{uploaded_file.name.split('.')[-1]}"
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"Uploaded {uploaded_file.name} for exercise {exercise_edit}")
                
                # Display current image and delete option
                image_path_jpg = f"exercise_images/{selected_exercise['Exercise']}.jpg"
                image_path_png = f"exercise_images/{selected_exercise['Exercise']}.png"
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
                    data.loc[selected_exercise.name, 'exercise'] = exercise_edit
                    data.loc[selected_exercise.name, 'volume'] = volume_edit
                    data.loc[selected_exercise.name, 'notes'] = notes_edit
                    data.to_csv('exercise_database.csv', index=False)
                    st.success('Exercise updated successfully!')
                    st.experimental_rerun()

# Custom CSS for button styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #1E90FF;
        border: 1px solid #1E90FF;
        border-radius: 5px;
        color: #ffffff;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #1E90FF;
        border: 1px solid #1E90FF;
    }
    .stButton>button:active {
        background-color: #1E90FF;
        border: 1px solid #1E90FF;
    }
    .stButton>button.selected {
        background-color: #1E90FF;
        color: #ffffff;
        border: 1px solid #1E90FF;
    }
    .stButton.export-button {
        width: auto;
    }
    .stButton>button.small-button {
        width: auto;
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
    </style>
    """, unsafe_allow_html=True)

# Hover-over text for disabled export button
if not (st.session_state['first_name'] and st.session_state['last_name'] and st.session_state['rehab_type']):
    st.markdown("""
        <script>
        const exportButton = document.querySelector('.stButton button:disabled');
        if (exportButton) {
            exportButton.setAttribute('title', 'Name and rehab type must be entered before exporting');
        }
        </script>
        """, unsafe_allow_html=True)

# Highlight the selected menu item
st.markdown(f"""
    <script>
    const buttons = document.querySelectorAll('.stButton>button');
    buttons.forEach((btn) => {{
        if (btn.innerText === "{menu_choice}") {{
            btn.classList.add('selected');
        }}
    }});
    </script>
    """, unsafe_allow_html=True)

# Sidebar footer
st.sidebar.markdown("""
    <div class="sidebar-footer">
        Catherine King<br>
        CK SPORTS PHYSIO<br>
        O Productions<br>
        Version 1.1
    </div>
    """, unsafe_allow_html=True)
