# streamlit_app/settings.py

import os
from pathlib import Path

import streamlit as st
from _common      import apply_global_css, page_header, get_base64_image
from utils        import get_client_db
from datetime     import date
import pandas as pd
import json

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Icons
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT       = Path(__file__).parent
BASE_DIR           = PROJECT_ROOT.parent         # your streamlit_app/ parent
PDF_DIR            = BASE_DIR / 'patient_pdfs'
CONTENT_DIR        = BASE_DIR / 'images'
USER_GROUPS_DB     = BASE_DIR / 'user_groups.db'
PATIENT_STATUS_DIR = BASE_DIR / 'patient_status'
SETTINGS_ICON      = CONTENT_DIR / 'settings.png'

# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────
def generate_client_id(conn):
    import random
    cur = conn.cursor()
    while True:
        cid = str(random.randint(10_000_000, 99_999_999))
        cur.execute("SELECT 1 FROM clients WHERE id=?", (cid,))
        if not cur.fetchone():
            return cid

def fetch_all_clients(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, account_type, first_name, last_name,
               mobile, email, password, status
        FROM clients
    """)
    return cur.fetchall()

def fetch_coaches(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name FROM clients WHERE account_type='Coach' AND status='active'")
    return cur.fetchall()

def fetch_athletes(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name FROM clients WHERE account_type='Athlete' AND status='active'")
    return cur.fetchall()

def fetch_user_groups(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT g.group_id, g.group_name,
               GROUP_CONCAT(DISTINCT CASE WHEN gm.role='Coach'   THEN c.first_name||' '||c.last_name END) AS coaches,
               GROUP_CONCAT(DISTINCT CASE WHEN gm.role='Athlete' THEN c.first_name||' '||c.last_name END) AS athletes
        FROM user_groups g
        LEFT JOIN group_members gm ON g.group_id=gm.group_id
        LEFT JOIN clients c      ON gm.member_id=c.id
        GROUP BY g.group_id, g.group_name
    """)
    rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["Group ID","Group Name","Coaches","Clients"])

def create_user_group(conn, name, coaches, athletes):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_groups(group_name,date_created) VALUES(?,?)",
        (name, date.today())
    )
    gid = cur.lastrowid
    for coach in coaches:
        cid = coach.split(" (ID: ")[1][:-1]
        cur.execute(
            "INSERT INTO group_members(group_id,member_id,role) VALUES(?,?,?)",
            (gid, cid, "Coach")
        )
    for ath in athletes:
        aid = ath.split(" (ID: ")[1][:-1]
        cur.execute(
            "INSERT INTO group_members(group_id,member_id,role) VALUES(?,?,?)",
            (gid, aid, "Athlete")
        )
    conn.commit()

def update_user_group(conn, gid, name, coaches, athletes):
    cur = conn.cursor()
    cur.execute("UPDATE user_groups SET group_name=? WHERE group_id=?", (name, gid))
    cur.execute("DELETE FROM group_members WHERE group_id=?", (gid,))
    for coach in coaches:
        cid = coach.split(" (ID: ")[1][:-1]
        cur.execute(
            "INSERT INTO group_members(group_id,member_id,role) VALUES(?,?,?)",
            (gid, cid, "Coach")
        )
    for ath in athletes:
        aid = ath.split(" (ID: ")[1][:-1]
        cur.execute(
            "INSERT INTO group_members(group_id,member_id,role) VALUES(?,?,?)",
            (gid, aid, "Athlete")
        )
    conn.commit()

# ──────────────────────────────────────────────────────────────────────────────
# Main renderer
# ──────────────────────────────────────────────────────────────────────────────
def render_settings():
    apply_global_css()
    page_header("Settings", icon_path=SETTINGS_ICON)

    conn   = get_client_db(USER_GROUPS_DB)
    cursor = conn.cursor()

    # --- Add New User ---
    st.write("### Add New User")
    c1, c2, c3 = st.columns(3)
    acct_type = c1.radio("Account Type", ["Athlete","Coach","Admin"], horizontal=True, key="new_acc_type")
    fn        = c2.text_input("First Name", key="new_first_name")
    ln        = c3.text_input("Last Name",  key="new_last_name")
    mcol, ecol, pcol = st.columns(3)
    mobile    = mcol.text_input("Mobile", key="new_mobile")
    email     = ecol.text_input("Email", key="new_email")
    pwd       = pcol.text_input("Password", type="password", key="new_password")

    st.markdown(
        f"<div style='text-align:right;'>Generated User ID: <b>{generate_client_id(conn)}</b></div>",
        unsafe_allow_html=True
    )

    if st.button("Add User", key="add_user_btn"):
        if not (fn and ln and email and pwd and mobile.isdigit()
                and len(mobile)==10 and mobile.startswith("04")):
            st.error("Please fill all fields correctly (mobile: 10 digits starting 04).")
        else:
            new_id = generate_client_id(conn)
            cursor.execute("""
                INSERT INTO clients(
                  id,account_type,first_name,last_name,
                  mobile,email,password,status
                ) VALUES (?,?,?,?,?,?,?,?)
            """, (new_id, acct_type, fn, ln, mobile, email, pwd, "active"))
            conn.commit()

            os.makedirs(PDF_DIR         / f"{ln}_{fn}_{new_id}", exist_ok=True)
            os.makedirs(PATIENT_STATUS_DIR / f"{ln}_{fn}_{new_id}", exist_ok=True)

            st.success(f"User {fn} {ln} added successfully!")

    st.markdown("---")

    # --- Users List & Edit ---
    st.write("### Users List")
    all_clients = fetch_all_clients(conn)
    df_clients  = pd.DataFrame(all_clients, columns=[
        "ID","Account Type","First Name","Last Name","Mobile","Email","Password","Status"
    ])
    st.dataframe(df_clients, use_container_width=True)

    st.write("### Edit User")
    opts = [""] + [f"{c[2]}_{c[3]}_{c[0]}" for c in all_clients]
    sel  = st.selectbox("Select User to Edit", opts, key="edit_user_select")
    if sel:
        uid  = sel.split("_")[-1]
        user = next(c for c in all_clients if c[0]==uid)
        e1,e2,e3,e4 = st.columns([0.3,0.3,0.3,0.1])
        etype  = e1.radio("Account Type", ["Athlete","Coach","Admin"],
                          index=["Athlete","Coach","Admin"].index(user[1]),
                          horizontal=True, key="edit_type")
        efn    = e2.text_input("First Name",  value=user[2], key="edit_fn")
        eln    = e3.text_input("Last Name",   value=user[3], key="edit_ln")
        estatus= e4.checkbox("Active", value=(user[7]=="active"), key="edit_status")
        mcol, ecol, pcol = st.columns(3)
        emobile = mcol.text_input("Mobile",  value=user[4], key="edit_mobile")
        eemail  = ecol.text_input("Email",   value=user[5], key="edit_email")
        epwd    = pcol.text_input("Password",value=user[6], type="password", key="edit_pwd")

        if st.button("Update User", key="update_user_btn"):
            cursor.execute("""
                UPDATE clients
                   SET account_type=?, first_name=?, last_name=?,
                       mobile=?, email=?, password=?, status=?
                 WHERE id=?
            """, (
                etype, efn, eln, emobile, eemail, epwd,
                "active" if estatus else "deactivated",
                uid
            ))
            conn.commit()
            st.success(f"User {efn} {eln} updated successfully!")

    st.markdown("---")

    # --- User Groups ---
    st.write("### Add User Group")
    group_name   = st.text_input("Group Name", key="grp_name")
    coach_list   = [f"{c[1]} {c[2]} (ID: {c[0]})" for c in fetch_coaches(conn)]
    athlete_list = [f"{a[1]} {a[2]} (ID: {a[0]})" for a in fetch_athletes(conn)]
    sel_coaches  = st.multiselect("Assign Coaches",  coach_list,   key="grp_coaches")
    sel_athletes = st.multiselect("Assign Athletes", athlete_list, key="grp_athletes")

    if st.button("Add User Group", key="add_grp_btn"):
        if not group_name.strip():
            st.error("Please provide a group name.")
        else:
            create_user_group(conn, group_name.strip(), sel_coaches, sel_athletes)
            st.success(f"User group '{group_name}' added successfully!")

    st.markdown("---")

    st.write("### Group List")
    df_groups = fetch_user_groups(conn)
    st.dataframe(df_groups, use_container_width=True)

    st.write("### Edit User Group")
    opts = [""] + [f"{int(r['Group ID'])} - {r['Group Name']}" for _,r in df_groups.iterrows()]
    selg = st.selectbox("Select Group to Edit", opts, key="edit_grp_select")
    if selg:
        gid  = int(selg.split(" - ")[0])
        row  = df_groups[df_groups["Group ID"]==gid].iloc[0]
        new_name = st.text_input("Group Name", value=row["Group Name"], key="edit_grp_name")

        def text_to_ids(txt):
            return [int(s.split(" (ID: ")[1][:-1])
                    for s in (txt or "").split(", ")
                    if "(ID:" in s]

        def find_defaults(source_list, existing_txt):
            chosen = text_to_ids(existing_txt)
            return [
                item for item in source_list
                if int(item.split(" (ID: ")[1][:-1]) in chosen
            ]

        default_coaches  = find_defaults(coach_list,  row["Coaches"])
        default_athletes = find_defaults(athlete_list,row["Clients"])

        edit_coaches  = st.multiselect("Assign Coaches",  coach_list,   default=default_coaches,  key="edit_grp_coaches")
        edit_athletes = st.multiselect("Assign Athletes",athlete_list, default=default_athletes, key="edit_grp_athletes")

        if st.button("Update User Group", key="update_grp_btn"):
            update_user_group(conn, gid, new_name, edit_coaches, edit_athletes)
            st.success(f"User group '{new_name}' updated successfully!")
