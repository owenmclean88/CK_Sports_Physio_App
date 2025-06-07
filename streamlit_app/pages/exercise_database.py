# streamlit_app/pages/05_Exercise_Database.py

import streamlit as st
from _common import apply_global_css, page_header, get_base64_image
from utils import load_data
from pathlib import Path
import pandas as pd
import os

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Icons
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT      = Path(__file__).parent.parent
CONTENT_DIR     = PROJECT_ROOT / 'images'
EXERCISE_CSV    = PROJECT_ROOT / 'exercise_database.csv'
EXERCISE_IMG_DIR= PROJECT_ROOT / 'exercise_images'
ICON            = CONTENT_DIR / 'database.png'

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def get_image_link(exercise: str) -> str:
    """Return an HTML link to the exercise image if it exists."""
    jpg = EXERCISE_IMG_DIR / f"{exercise}.jpg"
    png = EXERCISE_IMG_DIR / f"{exercise}.png"
    if jpg.exists():
        return f"<a href='{jpg}' target='_blank'>View Image</a>"
    if png.exists():
        return f"<a href='{png}' target='_blank'>View Image</a>"
    return "No Image"

# ──────────────────────────────────────────────────────────────────────────────
# Main render function
# ──────────────────────────────────────────────────────────────────────────────
def render_exercise_database():
    apply_global_css()
    page_header("Exercise Database", icon_path=ICON)

    st.write(
        '<span style="color: grey;">Adding filters from the dropdowns will reduce the exercises displayed in the table to assist you in finding what you\'re looking for.</span>',
        unsafe_allow_html=True
    )

    # Load data
    data = load_data()

    # Filters UI
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,0.5])
    if col5.button('Clear All'):
        for key in ['body_part_filter','movement_type_filter','sub_movement_type_filter','position_filter']:
            st.session_state.pop(key, None)

    body_part_filter      = col1.selectbox('Body Part', [""] + sorted(data['body_part'].astype(str).unique()), key='body_part_filter')
    movement_type_filter  = col2.selectbox('Movement Type', [""] + sorted(data['movement_type'].astype(str).unique()), key='movement_type_filter')
    sub_movement_type_filter = col3.selectbox('Sub Movement Type', [""] + sorted(data['sub_movement_type'].astype(str).unique()), key='sub_movement_type_filter')
    position_filter       = col4.selectbox('Position', [""] + sorted(data['position'].astype(str).unique()), key='position_filter')

    # Apply filters
    mask = True
    if body_part_filter:       mask &= data['body_part'] == body_part_filter
    if movement_type_filter:   mask &= data['movement_type'] == movement_type_filter
    if sub_movement_type_filter: mask &= data['sub_movement_type'] == sub_movement_type_filter
    if position_filter:        mask &= data['position'] == position_filter
    filtered = data[mask].copy()

    # Rename columns and add Image column
    filtered = filtered.rename(columns={
        'body_part': 'Body Part',
        'movement_type': 'Movement Type',
        'sub_movement_type': 'Sub Movement Type',
        'position': 'Position',
        'exercise': 'Exercise',
        'volume': 'Volume',
        'notes': 'Notes'
    })
    filtered['Image'] = filtered['Exercise'].apply(get_image_link)

    # Table styling
    st.markdown(
        """
        <style>
        .stDataFrame { max-height: 600px; }
        .stDataFrame td { white-space: normal; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Header with count
    total = len(filtered)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Exercise List</h3>
            <h4>Total Exercises: {total}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Display table
    st.dataframe(
        filtered[['Body Part','Movement Type','Sub Movement Type','Position','Exercise','Volume','Image','Notes']],
        use_container_width=True
    )

    # Edit exercise form
    options = [""] + [
        f"{r['Body Part']} - {r['Movement Type']} - {r['Sub Movement Type']} - {r['Position']} - {r['Exercise']}"
        for _, r in filtered.iterrows()
    ]
    selected = st.selectbox("Select Exercise to Edit", options, key='edit_exercise')
    if selected:
        idx = options.index(selected) - 1
        row = filtered.iloc[idx]
        st.write(f"Editing Exercise: **{row['Exercise']}**")

        with st.form(key='edit_form'):
            # Dropdowns for editing
            bp = st.selectbox('Body Part', sorted(data['body_part'].astype(str).unique()), index=list(data['body_part'].astype(str).unique()).index(row['Body Part']))
            mt = st.selectbox('Movement Type', sorted(data[data['body_part']==bp]['movement_type'].astype(str).unique()), index=list(data[data['body_part']==bp]['movement_type'].astype(str).unique()).index(row['Movement Type']))
            smt = st.selectbox('Sub Movement Type', sorted(data[(data['body_part']==bp)&(data['movement_type']==mt)]['sub_movement_type'].astype(str).unique()), index=list(data[(data['body_part']==bp)&(data['movement_type']==mt)]['sub_movement_type'].astype(str).unique()).index(row['Sub Movement Type']))
            pos = st.selectbox('Position', sorted(data[(data['body_part']==bp)&(data['movement_type']==mt)&(data['sub_movement_type']==smt)]['position'].astype(str).unique()), index=list(data[(data['body_part']==bp)&(data['movement_type']==mt)&(data['sub_movement_type']==smt)]['position'].astype(str).unique()).index(row['Position']))
            ex = st.text_input('Exercise', value=row['Exercise'])
            vol = st.text_input('Volume', value=str(row['Volume']))
            notes = st.text_area('Notes', value=row['Notes'])

            # Image upload
            uploaded = st.file_uploader("Upload Image", type=['jpg','png'])
            if uploaded:
                ext = uploaded.name.split('.')[-1]
                path = EXERCISE_IMG_DIR / f"{ex}.{ext}"
                with open(path, 'wb') as f: f.write(uploaded.getbuffer())
                st.success(f"Uploaded {uploaded.name}")

            # Show existing image if present
            for ext in ('jpg','png'):
                ip = EXERCISE_IMG_DIR / f"{row['Exercise']}.{ext}"
                if ip.exists():
                    b64 = get_base64_image(ip)
                    st.image(f"data:image/{ext};base64,{b64}", width=200)
                    break

            save = st.form_submit_button("Save Changes")
            if save:
                df = pd.read_csv(EXERCISE_CSV)
                mask2 = (
                    (df['body_part'] == row['Body Part']) &
                    (df['movement_type'] == row['Movement Type']) &
                    (df['sub_movement_type'] == row['Sub Movement Type']) &
                    (df['position'] == row['Position']) &
                    (df['exercise'] == row['Exercise'])
                )
                df.loc[mask2, 'body_part']          = bp
                df.loc[mask2, 'movement_type']      = mt
                df.loc[mask2, 'sub_movement_type']  = smt
                df.loc[mask2, 'position']           = pos
                df.loc[mask2, 'exercise']           = ex
                df.loc[mask2, 'volume']             = vol
                df.loc[mask2, 'notes']              = notes
                df.to_csv(EXERCISE_CSV, index=False)
                st.success("Exercise updated successfully!")
                st.experimental_rerun()

if __name__ == '__main__':
    render_exercise_database()
