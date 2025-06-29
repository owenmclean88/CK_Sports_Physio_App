# streamlit_app/pages/modify_program.py

import streamlit as st
import pandas as pd
import json
import os
from datetime import date
from pathlib import Path

from streamlit_app._common import apply_global_css, page_header, get_base64_image
from streamlit_app.utils import get_client_db, load_data

# ─── Paths & Constants ─────────────────────────────────────────────────────────
# ROOT now points to the 'streamlit_app' directory,
# as Path(__file__) is 'streamlit_app/pages/modify_program.py'
# and Path(__file__).parent.parent resolves to 'streamlit_app/'
ROOT             = Path(__file__).parent.parent
CONTENT_DIR      = ROOT / "images"
PDF_DIR          = ROOT / "patient_pdfs"
EXERCISE_IMG_DIR = ROOT / "exercise_images"


# ─── Session‐State Init & Clear ────────────────────────────────────────────────
def initialize_modify_program_state():
    st.session_state.setdefault("program_loaded", False)
    st.session_state.setdefault("selected_patient_modify", "")
    st.session_state.setdefault("selected_file_modify", "")
    # do NOT set session_type here!


def clear_program_fields():
    # remove all per-program fields (including session_type)
    for k in list(st.session_state.keys()):
        if k in (
            "first_name","last_name","rehab_type",
            "prescription_date","extra_comments","session_type"
        ) or k.startswith((
            "body_part_","movement_type_","sub_movement_type_",
            "position_","exercise_","volume_","notes_","progressions_"
        )):
            st.session_state.pop(k, None)
    st.session_state["program_loaded"] = False


# ─── Load / Save Helpers ───────────────────────────────────────────────────────
def load_existing_patients():
    patients = {}
    if PDF_DIR.exists():
        for folder in os.listdir(PDF_DIR):
            p = PDF_DIR / folder
            if p.is_dir() and folder != "archived_clients":
                js = [f.name for f in p.iterdir() if f.suffix == ".json"]
                if js:
                    patients[folder] = js
    return patients


def load_program_callback():
    pat = st.session_state["selected_patient_modify"]
    fn  = st.session_state["selected_file_modify"]
    if not (pat and fn):
        return

    full = PDF_DIR / pat / fn
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"Failed to open {full}: {e}")
        clear_program_fields()
        return

    # clear any old fields
    clear_program_fields()

    # simple fields
    st.session_state["first_name"]   = data.get("firstname", "")
    st.session_state["last_name"]    = data.get("lastname", "")
    st.session_state["rehab_type"]   = data.get("rehab_type", "")
    try:
        st.session_state["prescription_date"] = date.fromisoformat(data.get("prescription_date",""))
    except:
        st.session_state["prescription_date"] = date.today()
    st.session_state["extra_comments"] = data.get("extra_comments","")

    # this is the key we’ll use once we render the form
    st.session_state["session_type"] = data.get("session_type","Prehab")

    # load exercises into session_state keys
    exs = data.get("exercises", [])
    st.session_state["exercises"] = list(range(len(exs)))
    for i, ex in enumerate(exs):
        for field, val in ex.items():
            st.session_state[f"{field}_{i}"] = val

    st.session_state["program_loaded"] = True
    st.success(f"Loaded program {fn}")


def save_modified_program_json(client_id: str, exercises_list):
    payload = {
        "firstname"        : st.session_state["first_name"],
        "lastname"         : st.session_state["last_name"],
        "rehab_type"       : st.session_state["rehab_type"],
        "prescription_date": str(st.session_state["prescription_date"]),
        "session_type"     : st.session_state["session_type"],
        "exercises"        : exercises_list,
        "extra_comments"   : st.session_state["extra_comments"],
    }
    folder = f"{payload['lastname']}_{payload['firstname']}_{client_id}"
    outdir = PDF_DIR / folder
    outdir.mkdir(parents=True, exist_ok=True)

    fname = f"{payload['lastname']}_{payload['firstname']}_{payload['rehab_type']}_{payload['prescription_date']}.json"
    (outdir / fname).write_text(
        json.dumps(payload, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )
    st.success("Program updates saved!")


# ─── Exercise Rendering (unchanged) ────────────────────────────────────────────
# NOTE: The content of render_exercise_fields and render_preview_section
# was commented out as '... your existing implementation ...' in your provided code.
# I am assuming these functions are correctly defined elsewhere in your full file
# and have not changed their logic.

def render_exercise_fields(df: pd.DataFrame):
    """Render all of the selectboxes/inputs for each exercise in session_state.exercises"""
    ex_list = []
    for i in range(len(st.session_state.exercises)):
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.25,1,1,1,1,0.15,0.15,0.15])
        c1.write(f"{i+1}.")
        bp   = c2.selectbox(f"Body Part {i+1}", [""] + sorted(df.body_part.unique()), key=f"body_part_{i}")
        mdf  = df[df.body_part==bp] if bp else df.iloc[0:0]
        mt   = c3.selectbox(f"Movement Type {i+1}", [""] + sorted(mdf.movement_type.unique()), key=f"movement_type_{i}")
        smd  = mdf[mdf.movement_type==mt] if mt else mdf.iloc[0:0]
        smt  = c4.selectbox(f"Sub-Movement {i+1}", [""] + sorted(smd.sub_movement_type.unique()), key=f"sub_movement_type_{i}")
        pdfd = smd[smd.sub_movement_type==smt] if smt else smd.iloc[0:0]
        pos  = c5.selectbox(f"Position {i+1}", [""] + sorted(pdfd.position.unique()), key=f"position_{i}")

        if i>0:
            c6.button("↑", key=f"up_{i}",   on_click=lambda i=i: swap_exercises(i,i-1)) # Added lambda for closure
        if i < len(st.session_state.exercises)-1:
            c7.button("↓", key=f"down_{i}", on_click=lambda i=i: swap_exercises(i,i+1)) # Added lambda for closure
        c8.button("🗑️", key=f"del_{i}", on_click=lambda i=i: delete_exercise(i)) # Added lambda for closure

        e1,e2,e3 = st.columns([0.25,2,2])
        exn = e2.selectbox(f"Exercise {i+1}", [""] + sorted(pdfd.exercise.unique()), key=f"exercise_{i}")
        vol = e3.text_input(f"Volume {i+1}", key=f"volume_{i}",
                                 value=str(pdfd.iloc[0].volume) if (not pdfd.empty and exn) else "")

        n1,n2,n3 = st.columns([0.25,2,2])
        notes    = n2.text_input(f"Notes {i+1}", key=f"notes_{i}")
        progs    = n3.text_input(f"Progressions {i+1}", key=f"progressions_{i}")

        if i < len(st.session_state.exercises)-1:
            st.divider()

        ex_list.append({
            "body_part": bp,
            "movement_type": mt,
            "sub_movement_type": smt,
            "position": pos,
            "exercise": exn,
            "volume": vol,
            "notes": notes,
            "progressions": progs,
        })

    st.button("Add Exercise", on_click=add_exercise)
    return ex_list


def render_preview_section(exs):
    """A simple in-page mock-PDF preview, no fpdf involved."""
    with st.expander("Preview Program PDF", expanded=False):
        logo = CONTENT_DIR / "company_logo3.png"
        if logo.exists():
            st.image(str(logo), width=100)
        st.markdown(f"## {st.session_state['rehab_type']}", unsafe_allow_html=True)
        st.write(f"**Patient:** {st.session_state['first_name']} {st.session_state['last_name']}")
        st.write(f"**Date:** {st.session_state['prescription_date']}")
        for m in sorted({e["movement_type"] for e in exs}):
            st.markdown(f"### {m}")
            for e in [x for x in exs if x["movement_type"]==m]:
                st.write(f"**{e['exercise']}** — {e['body_part']} / {e['position']} / {e['volume']}")
                img = EXERCISE_IMG_DIR / f"{e['exercise']}.png"
                if not img.exists():
                    img = EXERCISE_IMG_DIR / f"{e['exercise']}.jpg"
                if img.exists():
                    st.image(str(img), width=100)
        st.markdown("#### Comments")
        st.write(st.session_state["extra_comments"])


# ─── Main Page ─────────────────────────────────────────────────────────────────
def render_modify_program():
    apply_global_css()
    page_header("Modify Program", icon_path=CONTENT_DIR/"refresh.png")

    initialize_modify_program_state()

    # — Load controls
    st.markdown("### Load Existing Program")
    patients = load_existing_patients()

    st.selectbox(
        "Select Patient",
        [""] + sorted(patients.keys()),
        key="selected_patient_modify"
    )
    if st.session_state.selected_patient_modify:
        st.selectbox(
            "Select Program File",
            [""] + sorted(patients[st.session_state.selected_patient_modify]),
            key="selected_file_modify"
        )

    st.button(
        "Load Program",
        on_click=load_program_callback,
        disabled=not (st.session_state.selected_patient_modify and st.session_state.selected_file_modify)
    )

    # — bail out if nothing loaded yet
    if not st.session_state.program_loaded:
        st.info("Please load a program to edit.")
        return

    # — now the form widgets are created **only after** program_loaded=True
    st.markdown("---")
    st.write("### Program Details")
    c1, c2, c3 = st.columns([2,2,1])

    # radio is safe because it's first instantiated here
    opts = ["Prehab","Rehab","Recovery"]
    curr = st.session_state.get("session_type","Prehab")
    idx  = opts.index(curr) if curr in opts else 0
    c2.radio("Session Type", opts, index=idx, key="session_type", horizontal=True)

    c1.text_input("Patient First Name", key="first_name", value=st.session_state["first_name"])
    c1.text_input("Patient Last Name",  key="last_name",  value=st.session_state["last_name"])
    c2.text_input("Session Name",       key="rehab_type", value=st.session_state["rehab_type"])
    c3.date_input("Prescription Date",  key="prescription_date", value=st.session_state["prescription_date"])

    st.write("### Exercises")
    df  = load_data()
    exs = render_exercise_fields(df)

    st.markdown("## Session Notes")
    st.text_area("Additional comments", key="extra_comments", value=st.session_state["extra_comments"])

    render_preview_section(exs)

    if st.button("Save Updates", disabled=not (st.session_state["rehab_type"] and any(e.get("exercise") for e in exs))):
        cid = st.session_state.selected_patient_modify.split("_")[-1]
        save_modified_program_json(cid, exs)


if __name__ == "__main__":
    render_modify_program()