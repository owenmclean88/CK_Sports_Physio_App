# streamlit_app/pages/new_program.py

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date
import json

from _common           import apply_global_css, page_header
from utils             import get_client_db, load_data

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Constants
# ──────────────────────────────────────────────────────────────────────────────
# ROOT now points to the 'streamlit_app' directory,
# as Path(__file__) is 'streamlit_app/pages/new_program.py'
# and Path(__file__).parent.parent resolves to 'streamlit_app/'
ROOT             = Path(__file__).parent.parent
CONTENT_DIR      = ROOT / "images"
PDF_DIR          = ROOT / "patient_pdfs"
EXERCISE_IMG_DIR = ROOT / "exercise_images" # Assuming exercise_images is also directly in streamlit_app/

# ──────────────────────────────────────────────────────────────────────────────
def initialize_exercise_state():
    st.session_state.setdefault("exercises", [0])

def add_exercise():
    st.session_state.exercises.append(len(st.session_state.exercises))

def swap_exercises(i1, i2):
    keys = ["body_part","movement_type","sub_movement_type",
            "position","exercise","volume","notes","progressions"]
    for k in keys:
        a, b = f"{k}_{i1}", f"{k}_{i2}"
        st.session_state[a], st.session_state[b] = (
            st.session_state.get(b, ""), st.session_state.get(a, "")
        )

def delete_exercise(idx):
    keys = ["body_part","movement_type","sub_movement_type",
            "position","exercise","volume","notes","progressions"]
    for k in keys:
        # shift everything after idx back one slot
        for j in range(idx, len(st.session_state.exercises)-1):
            st.session_state[f"{k}_{j}"] = st.session_state.get(f"{k}_{j+1}", "")
        # pop the last
        st.session_state.pop(f"{k}_{len(st.session_state.exercises)-1}", None)
    st.session_state.exercises.pop()

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
            c6.button("↑", key=f"up_{i}",   on_click=swap_exercises, args=(i,i-1))
        if i < len(st.session_state.exercises)-1:
            c7.button("↓", key=f"down_{i}", on_click=swap_exercises, args=(i,i+1))
        c8.button("🗑️", key=f"del_{i}", on_click=delete_exercise, args=(i,))

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

# ──────────────────────────────────────────────────────────────────────────────
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

def save_to_json(cid, exs):
    """Persist session to a JSON file in the client’s folder."""
    folder = f"{st.session_state['last_name']}_{st.session_state['first_name']}_{cid}"
    path   = PDF_DIR / folder
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "firstname":           st.session_state["first_name"],
        "lastname":            st.session_state["last_name"],
        "rehab_type":          st.session_state["rehab_type"],
        "prescription_date": str(st.session_state["prescription_date"]),
        "exercises":           exs,
        "extra_comments":      st.session_state["extra_comments"],
    }
    fname = f"{payload['lastname']}_{payload['firstname']}_{payload['rehab_type']}_{payload['prescription_date']}.json"
    with open(path/fname, "w", encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

# ──────────────────────────────────────────────────────────────────────────────
def render_new_program():
    apply_global_css()
    page_header("New Program", icon_path=CONTENT_DIR/"plus-circle.png")

    initialize_exercise_state()
    data = load_data()
    conn = get_client_db()

    athletes = conn.execute(
        "SELECT id, first_name, last_name FROM clients WHERE account_type='Athlete' AND status='active'"
    ).fetchall()
    opts = [f"{a[1]} {a[2]} (ID: {a[0]})" for a in athletes]

    c1,c2,c3 = st.columns([2,2,1])
    sel = c1.selectbox("Select Client", [""]+opts, key="selected_client")
    if sel:
        cid = sel.split("(ID: ")[1][:-1]
        fn,ln = next(a for a in athletes if a[0]==cid)[1:]
        st.session_state["first_name"], st.session_state["last_name"] = fn, ln
    else:
        cid = None

    c2.radio("Session Type", ["Prehab","Rehab","Recovery"], horizontal=True, key="session_type")
    c2.text_input("Session Name", key="rehab_type")
    c3.date_input("Prescription Date", date.today(), key="prescription_date")

    st.write("### Exercises")
    exs = render_exercise_fields(data)

    st.markdown("## Session Notes")
    st.text_area("Additional comments", key="extra_comments")

    # only show preview + JSON-save—no more PDF generation at all
    if cid and st.session_state["rehab_type"] and any(e["exercise"] for e in exs):
        render_preview_section(exs)
        if st.button("Save Session Only"):
            save_to_json(cid, exs)
            st.success("Session saved.")

if __name__=="__main__":
    render_new_program()