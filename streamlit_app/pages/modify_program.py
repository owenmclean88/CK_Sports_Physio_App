# streamlit_app/pages/02_Modify_Program.py

import streamlit as st
import pandas as pd
from typing import List, Dict
from _common import apply_global_css, page_header, get_base64_image
from utils import get_client_db, load_data
from datetime import date
from pathlib import Path
from fpdf import FPDF
import os
import json

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT      = Path(__file__).parent.parent
CONTENT_DIR     = PROJECT_ROOT / 'images'
PDF_DIR         = PROJECT_ROOT / 'patient_pdfs'
EXERCISE_IMG_DIR= PROJECT_ROOT / 'exercise_images'

# ──────────────────────────────────────────────────────────────────────────────
# Session‐State Initialization
# ──────────────────────────────────────────────────────────────────────────────
def initialize_session_state():
    if 'exercises'    not in st.session_state: st.session_state.exercises    = [0]
    if 'rehab_type'   not in st.session_state: st.session_state.rehab_type   = ''
    if 'extra_comments' not in st.session_state: st.session_state.extra_comments = ''
    if 'session_type' not in st.session_state: st.session_state.session_type = 'Prehab'

# ──────────────────────────────────────────────────────────────────────────────
# Add / Remove Exercise Helpers
# ──────────────────────────────────────────────────────────────────────────────
def add_exercise():
    st.session_state.exercises.append(len(st.session_state.exercises))

# ──────────────────────────────────────────────────────────────────────────────
# Exercise Field Rendering (Modify Page)
# ──────────────────────────────────────────────────────────────────────────────

def swap_exercises(i1, i2):
    keys = ['body_part','movement_type','sub_movement_type',
            'position','exercise','volume','notes','progressions']
    for k in keys:
        a, b = f"{k}_{i1}", f"{k}_{i2}"
        st.session_state[a], st.session_state[b] = (
            st.session_state.get(b, ""), st.session_state.get(a, "")
        )

def delete_exercise(idx):
    keys = ['body_part','movement_type','sub_movement_type',
            'position','exercise','volume','notes','progressions']
    for k in keys:
        for j in range(idx, len(st.session_state.exercises)-1):
            st.session_state[f"{k}_{j}"] = st.session_state.get(f"{k}_{j+1}", "")
        st.session_state.pop(f"{k}_{len(st.session_state.exercises)-1}", None)
    st.session_state.exercises.pop()

def render_exercise_fields(data: pd.DataFrame) -> List[Dict]:
    selected = []
    for i in range(len(st.session_state.exercises)):
        cols1 = st.columns([0.25,1,1,1,1,0.15,0.15,0.15])
        cols1[0].write(f"{i+1}.")

        # Body part → movement → sub-movement
        bp  = cols1[1].selectbox(
            f"Body Part {i+1}",
            [""] + list(data['body_part'].unique()),
            key=f"body_part_{i}"
        )
        mdf = data[data['body_part']==bp] if bp else data.iloc[0:0]

        mt  = cols1[2].selectbox(
            f"Movement Type {i+1}",
            [""] + list(mdf['movement_type'].unique()),
            key=f"movement_type_{i}"
        )
        smdf = mdf[mdf['movement_type']==mt] if mt else mdf.iloc[0:0]

        smt = cols1[3].selectbox(
            f"Sub-Movement {i+1}",
            [""] + list(smdf['sub_movement_type'].unique()),
            key=f"sub_movement_type_{i}"
        )
        # rename filtered DF to avoid name clash
        pos_df = smdf[smdf['sub_movement_type']==smt] if smt else smdf.iloc[0:0]

        pos = cols1[4].selectbox(
            f"Position {i+1}",
            [""] + list(pos_df['position'].unique()),
            key=f"position_{i}"
        )

        # Up / Down / Delete
        if i > 0:
            cols1[5].button("↑", key=f"up_{i}", on_click=swap_exercises, args=(i, i-1))
        if i < len(st.session_state.exercises)-1:
            cols1[6].button("↓", key=f"down_{i}", on_click=swap_exercises, args=(i, i+1))
        cols1[7].button("🗑️", key=f"del_{i}", on_click=delete_exercise, args=(i,))

        # Exercise & Volume
        cols2 = st.columns([0.25,2,2])
        edf = pos_df[pos_df['position']==pos] if pos else pos_df.iloc[0:0]

        exn = cols2[1].selectbox(
            f"Exercise {i+1}",
            [""] + list(edf['exercise'].unique()),
            key=f"exercise_{i}"
        )
        vol = cols2[2].text_input(
            f"Volume {i+1}",
            key=f"volume_{i}",
            value=(
                str(edf.iloc[0]['volume'])
                if not edf[edf['exercise']==exn].empty
                else ""
            )
        )

        # Notes & Progressions
        cols3 = st.columns([0.25,2,2])
        notes       = cols3[1].text_input(f"Notes {i+1}", key=f"notes_{i}")
        progressions= cols3[2].text_input(f"Progressions {i+1}", key=f"progressions_{i}")

        if i < len(st.session_state.exercises)-1:
            st.divider()

        selected.append({
            'body_part':         bp,
            'movement_type':     mt,
            'sub_movement_type': smt,
            'position':          pos,
            'exercise':          exn,
            'volume':            vol,
            'notes':             notes,
            'progressions':      progressions
        })

    st.button("Add Exercise", on_click=add_exercise)
    return selected

# ──────────────────────────────────────────────────────────────────────────────
# PDF & Preview Helpers
# ──────────────────────────────────────────────────────────────────────────────
def generate_pdf(pdf: FPDF, exs):
    pdf.image(CONTENT_DIR / 'company_logo3.png',10,8,33)
    pdf.set_font("Arial",size=12); pdf.set_xy(150,10)
    pdf.multi_cell(50,10,"Catherine King\nSports Physiotherapist\n0438503185",align='R')
    pdf.ln(15); pdf.set_font("Arial",'B',16); pdf.cell(0,10,st.session_state['rehab_type'],ln=True)
    pdf.set_font("Arial",size=12)
    pdf.cell(0,6,f"Patient: {st.session_state['first_name']} {st.session_state['last_name']}",ln=True)
    pdf.cell(0,6,f"Date: {st.session_state['prescription_date']}",ln=True); pdf.ln(5)
    for m in sorted({e['movement_type'] for e in exs}):
        pdf.set_font("Arial",'B',12); pdf.cell(0,8,m,ln=True)
        pdf.set_font("Arial",size=10)
        for e in [x for x in exs if x['movement_type']==m]:
            line = f"{e['exercise']} — Body: {e['body_part']}, Pos: {e['position']}, Vol: {e['volume']}"
            pdf.multi_cell(0,6,line)
            ip = EXERCISE_IMG_DIR / f"{e['exercise']}.png"
            if not ip.exists(): ip = EXERCISE_IMG_DIR / f"{e['exercise']}.jpg"
            if ip.exists():
                y=pdf.get_y(); pdf.image(str(ip),x=160,y=y,w=30,h=30); pdf.ln(30)
        pdf.ln(2)
    pdf.set_font("Arial",'B',12); pdf.cell(0,8,"Extra Comments",ln=True)
    pdf.set_font("Arial",size=10); pdf.multi_cell(0,6,st.session_state['extra_comments'])

def render_preview_section(exs):
    with st.expander("Preview Program PDF"):
        for m in sorted({e['movement_type'] for e in exs}):
            st.write(f"### {m}")
            for e in [x for x in exs if x['movement_type']==m]:
                st.write(f"**{e['exercise']}** — Body: {e['body_part']}, Pos: {e['position']}, Vol: {e['volume']}")
                ip = EXERCISE_IMG_DIR / f"{e['exercise']}.png"
                if not ip.exists(): ip = EXERCISE_IMG_DIR / f"{e['exercise']}.jpg"
                if ip.exists(): st.image(str(ip), width=100)
        st.write("#### Extra Comments"); st.write(st.session_state['extra_comments'])

# ──────────────────────────────────────────────────────────────────────────────
# Load & Save Session JSON
# ──────────────────────────────────────────────────────────────────────────────
def load_existing_patients():
    patients = {}
    if PDF_DIR.exists():
        for folder in os.listdir(PDF_DIR):
            if folder == 'archived_clients': continue
            files = [f for f in os.listdir(PDF_DIR / folder) if f.endswith('.json')]
            patients[folder] = files
    return patients

def load_session_from_json(sel):
    folder, fname = sel.split('/',1)
    path = PDF_DIR / folder / fname
    d = json.load(open(path))
    st.session_state['first_name']    = d['firstname']
    st.session_state['last_name']     = d['lastname']
    st.session_state['rehab_type']    = d['rehab_type']
    st.session_state['prescription_date'] = date.fromisoformat(d['prescription_date'])
    st.session_state['extra_comments']= d['extra_comments']
    st.session_state.exercises = list(range(len(d['exercises'])))
    for i, ex in enumerate(d['exercises']):
        for k in ['body_part','movement_type','sub_movement_type','position','exercise','volume','notes','progressions']:
            st.session_state[f"{k}_{i}"] = ex[k]

def save_session_to_json(client_id, exs):
    folder = f"{st.session_state['last_name']}_{st.session_state['first_name']}_{client_id}"
    path = PDF_DIR / folder
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        'firstname': st.session_state['first_name'],
        'lastname':  st.session_state['last_name'],
        'rehab_type':st.session_state['rehab_type'],
        'prescription_date': str(st.session_state['prescription_date']),
        'exercises': exs,
        'extra_comments': st.session_state['extra_comments']
    }
    fname = f"{payload['lastname']}_{payload['firstname']}_{payload['rehab_type']}_{payload['prescription_date']}.json"
    with open(path / fname, 'w') as f:
        json.dump(payload, f)

# ──────────────────────────────────────────────────────────────────────────────
# Page Renderer
# ──────────────────────────────────────────────────────────────────────────────
def render_modify_program():
    apply_global_css()
    page_header("Modify Program", icon_path=CONTENT_DIR / 'refresh.png')
    initialize_session_state()

    data = load_data()
    conn = get_client_db()

    patients = load_existing_patients()
    sel_pat = st.selectbox("Select Patient", [""] + list(patients.keys()))
    if sel_pat:
        sel_file = st.selectbox("Select Session", [""] + patients[sel_pat])
        if sel_file and st.button("Load Program"):
            load_session_from_json(f"{sel_pat}/{sel_file}")

    # Edit form
    col1, col2, col3 = st.columns([2,2,1])
    st.session_state.session_type = col2.radio("Session Type", ["Prehab","Rehab","Recovery"],
                                               horizontal=True, key="session_type")
    st.session_state.rehab_type   = col2.text_input("Session Name", key="rehab_type")
    st.session_state.prescription_date = col3.date_input("Prescription Date",
                                               value=date.today(), key="prescription_date")

    st.write("### Exercises")
    exs = render_exercise_fields(data)

    st.markdown("## Session Notes")
    st.text_area("Additional comments", key="extra_comments")

    valid = sel_pat and st.session_state['rehab_type'] and any(e['exercise'] for e in exs)
    if valid:
        render_preview_section(exs)
        if st.button("Save Session Only"):
            cid = sel_pat.split("_")[-1]
            save_session_to_json(cid, exs)
            st.success("Session saved.")

        pdf = FPDF(); pdf.add_page(); generate_pdf(pdf, exs)
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        if st.download_button(
            "Save & Export to PDF",
            data=pdf_bytes,
            file_name=f"{st.session_state['last_name']}_{st.session_state['first_name']}_{st.session_state['rehab_type']}_{st.session_state['prescription_date']}.pdf",
            mime="application/pdf"
        ):
            cid = sel_pat.split("_")[-1]
            save_session_to_json(cid, exs)
            st.success("PDF exported.")

# ──────────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_modify_program()
