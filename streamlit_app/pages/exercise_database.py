# streamlit_app/pages/05_Exercise_Database.py

import streamlit as st
from _common import apply_global_css, page_header, get_base64_image
from utils import get_client_db
from pathlib import Path
import pandas as pd
import os

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Icons
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT_OF_PAGE = Path(__file__).parent
STREAMLIT_APP_DIR = PROJECT_ROOT_OF_PAGE.parent
PROJECT_ROOT = STREAMLIT_APP_DIR.parent

CONTENT_DIR = STREAMLIT_APP_DIR / 'images'
EXERCISE_IMG_DIR = STREAMLIT_APP_DIR / 'exercise_images'

EXERCISE_CSV = PROJECT_ROOT / 'exercise_database.csv'
ICON = CONTENT_DIR / 'database.png'

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def get_image_link(exercise: str) -> str:
    """Return an HTML link to the exercise image if it exists."""
    if not EXERCISE_IMG_DIR.exists():
        return "No Image Dir"

    jpg = EXERCISE_IMG_DIR / f"{exercise}.jpg"
    png = EXERCISE_IMG_DIR / f"{exercise}.png"

    if jpg.exists():
        return f"<a href='file:///{jpg.resolve()}' target='_blank'>View JPG</a>"
    if png.exists():
        return f"<a href='file:///{png.resolve()}' target='_blank'>View PNG</a>"
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
    if not EXERCISE_CSV.exists():
        st.error(f"Exercise database CSV not found at: {EXERCISE_CSV}. Please ensure 'exercise_database.csv' is in your project root.")
        st.stop()

    # FIX: Specify encoding for reading the CSV
    data = pd.read_csv(EXERCISE_CSV, encoding='windows-1252')

    for col in ['body_part', 'movement_type', 'sub_movement_type', 'position', 'exercise']:
        if col in data.columns:
            data[col] = data[col].astype(str).fillna('')

    # Filters UI
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,0.5])
    if col5.button('Clear All Filters', key='clear_filters_btn'):
        for key in ['body_part_filter','movement_type_filter','sub_movement_type_filter','position_filter']:
            st.session_state.pop(key, None)
        st.rerun()

    body_parts_options = [""] + sorted(data['body_part'].unique())
    movement_types_options = [""] + sorted(data['movement_type'].unique())
    sub_movement_types_options = [""] + sorted(data['sub_movement_type'].unique())
    position_options = [""] + sorted(data['position'].unique())

    body_part_filter = col1.selectbox('Body Part', body_parts_options, key='body_part_filter')
    movement_type_filter = col2.selectbox('Movement Type', movement_types_options, key='movement_type_filter')
    sub_movement_type_filter = col3.selectbox('Sub Movement Type', sub_movement_types_options, key='sub_movement_type_filter')
    position_filter = col4.selectbox('Position', position_options, key='position_filter')

    # Apply filters
    mask = pd.Series(True, index=data.index)

    if body_part_filter:
        mask &= (data['body_part'] == body_part_filter)
    if movement_type_filter:
        mask &= (data['movement_type'] == movement_type_filter)
    if sub_movement_type_filter:
        mask &= (data['sub_movement_type'] == sub_movement_type_filter)
    if position_filter:
        mask &= (data['position'] == position_filter)
    
    filtered = data[mask].copy()

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

    st.markdown(
        """
        <style>
        .stDataFrame { max-height: 600px; }
        .stDataFrame td { white-space: normal; }
        </style>
        """,
        unsafe_allow_html=True
    )

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

    st.dataframe(
        filtered[['Body Part','Movement Type','Sub Movement Type','Position','Exercise','Volume','Image','Notes']],
        use_container_width=True,
    )

    options = [""] + [
        f"{r['body_part']} - {r['movement_type']} - {r['sub_movement_type']} - {r['position']} - {r['exercise']}"
        for _, r in data.iterrows()
    ]
    selected = st.selectbox("Select Exercise to Edit", options, key='edit_exercise')

    if selected:
        parts = selected.split(" - ")
        if len(parts) == 5:
            selected_body_part, selected_movement_type, selected_sub_movement_type, selected_position, selected_exercise = parts

            row_mask = (data['body_part'] == selected_body_part) & \
                       (data['movement_type'] == selected_movement_type) & \
                       (data['sub_movement_type'] == selected_sub_movement_type) & \
                       (data['position'] == selected_position) & \
                       (data['exercise'] == selected_exercise)

            if row_mask.any():
                row = data[row_mask].iloc[0]
                st.write(f"Editing Exercise: **{row['exercise']}**")

                with st.form(key='edit_form'):
                    bp_idx = body_parts_options.index(row['body_part']) if row['body_part'] in body_parts_options else 0
                    bp = st.selectbox('Body Part', body_parts_options, index=bp_idx, key="edit_bp")
                    
                    mt_options_filtered = [""] + sorted(data[data['body_part'] == bp]['movement_type'].unique())
                    mt_idx = mt_options_filtered.index(row['movement_type']) if row['movement_type'] in mt_options_filtered else 0
                    mt = st.selectbox('Movement Type', mt_options_filtered, index=mt_idx, key="edit_mt")

                    smt_options_filtered = [""] + sorted(data[(data['body_part'] == bp) & (data['movement_type'] == mt)]['sub_movement_type'].unique())
                    smt_idx = smt_options_filtered.index(row['sub_movement_type']) if row['sub_movement_type'] in smt_options_filtered else 0
                    smt = st.selectbox('Sub Movement Type', smt_options_filtered, index=smt_idx, key="edit_smt")

                    pos_options_filtered = [""] + sorted(data[(data['body_part'] == bp) & (data['movement_type'] == mt) & (data['sub_movement_type'] == smt)]['position'].unique())
                    pos_idx = pos_options_filtered.index(row['position']) if row['position'] in pos_options_filtered else 0
                    pos = st.selectbox('Position', pos_options_filtered, index=pos_idx, key="edit_pos")

                    ex = st.text_input('Exercise', value=row['exercise'], key="edit_ex")
                    vol = st.text_input('Volume', value=str(row['volume']), key="edit_vol")
                    notes = st.text_area('Notes', value=row['notes'], key="edit_notes")

                    uploaded = st.file_uploader("Upload New Image (overwrites existing)", type=['jpg','png'], key=f"img_uploader_{selected}")
                    if uploaded:
                        ext = uploaded.name.split('.')[-1]
                        for existing_ext in ('jpg', 'png'):
                            existing_path = EXERCISE_IMG_DIR / f"{row['exercise']}.{existing_ext}"
                            if existing_path.exists() and existing_path != (EXERCISE_IMG_DIR / f"{ex}.{ext}"):
                                os.remove(existing_path)
                        
                        path = EXERCISE_IMG_DIR / f"{ex}.{ext}"
                        EXERCISE_IMG_DIR.mkdir(parents=True, exist_ok=True)
                        with open(path, 'wb') as f: f.write(uploaded.getbuffer())
                        st.success(f"Uploaded {uploaded.name}. Image will update on rerun.")
                        st.rerun()

                    current_image_displayed = False
                    for ext_type in ('jpg','png'):
                        ip = EXERCISE_IMG_DIR / f"{row['exercise']}.{ext_type}"
                        if ip.exists():
                            b64 = get_base64_image(ip)
                            st.image(f"data:image/{ext_type};base64,{b64}", width=200, caption="Current Image")
                            current_image_displayed = True
                            break
                    if not current_image_displayed:
                        st.info("No existing image found for this exercise.")


                    save = st.form_submit_button("Save Changes")
                    if save:
                        df = pd.read_csv(EXERCISE_CSV, encoding='windows-1252') # Also update encoding here
                        
                        mask2 = (
                            (df['body_part'] == selected_body_part) &
                            (df['movement_type'] == selected_movement_type) &
                            (df['sub_movement_type'] == selected_sub_movement_type) &
                            (df['position'] == selected_position) &
                            (df['exercise'] == selected_exercise)
                        )
                        
                        if mask2.any():
                            df.loc[mask2, 'body_part'] = bp
                            df.loc[mask2, 'movement_type'] = mt
                            df.loc[mask2, 'sub_movement_type'] = smt
                            df.loc[mask2, 'position'] = pos
                            df.loc[mask2, 'exercise'] = ex
                            df.loc[mask2, 'volume'] = vol
                            df.loc[mask2, 'notes'] = notes
                            df.to_csv(EXERCISE_CSV, index=False, encoding='windows-1252') # And here for saving
                            st.success("Exercise updated successfully!")
                            st.rerun()
                        else:
                            st.error("Could not find the original exercise to update. Please re-select or check data consistency.")
            else:
                st.warning("Selected exercise not found in the original data for editing. This might indicate a data mismatch.")
        else:
            st.warning("Invalid exercise selection format for editing.")


if __name__ == '__main__':
    render_exercise_database()