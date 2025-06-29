# streamlit_app/pages/settings.py

import os
import sqlite3
import shutil
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from streamlit_app.utils import (
    get_client_db,
    generate_client_id,
    generate_username,
    fetch_all_clients_basic,
    fetch_all_groups,
    fetch_user_groups,
    assign_user_to_groups,
    insert_group_row,
    update_group_row,
    delete_group_row,
    delete_client,            # if implemented in utils; otherwise deletion is inline
)
from streamlit_app._common import apply_global_css, page_header, get_base64_image

# ──────────────────────────────────────────────────────────────────────────────
# Paths & Icons
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT       = Path(__file__).parent
BASE_DIR           = PROJECT_ROOT.parent      # streamlit_app/ parent
PDF_DIR            = BASE_DIR / 'patient_pdfs'
PATIENT_STATUS_DIR = BASE_DIR / 'patient_status'
CONTENT_DIR        = BASE_DIR / 'images'
SETTINGS_ICON      = CONTENT_DIR / 'settings.png'
BACKUP_DIR         = BASE_DIR / 'db_backups'

# Fixed options for Group Parent dropdown (if used elsewhere)
GROUP_PARENT_OPTIONS = ["Gymsport", "SportsMed", "Other"]

# ──────────────────────────────────────────────────────────────────────────────
def create_database_backup():
    """
    Creates a timestamped backup of client_database.db.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    db_path = BASE_DIR / 'client_database.db'
    if not db_path.exists():
        st.error("Cannot create backup: client_database.db not found.")
        return None, None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"client_database_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_filename
    try:
        shutil.copy2(db_path, backup_path)
        st.success(f"Database backup created: {backup_filename}")
        return backup_path, backup_filename
    except Exception as e:
        st.error(f"Error creating backup: {e}")
        return None, None

def ensure_username_column(conn: sqlite3.Connection):
    """
    Ensure that the 'username' column exists in clients table. If missing, ALTER TABLE to add it.
    """
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(clients)")
        cols = [row[1] for row in cur.fetchall()]
        if 'username' not in cols:
            # Add username column
            cur.execute("ALTER TABLE clients ADD COLUMN username TEXT")
            conn.commit()
    except Exception:
        # If table doesn't exist yet or other issues, ignore here
        pass

def render_settings():
    apply_global_css()
    page_header("Settings", icon_path=SETTINGS_ICON)

    # 1) Connect to DB
    conn = get_client_db()
    if conn is None:
        st.error("Cannot access client database.")
        return
    cursor = conn.cursor()

    # Ensure username column exists before using
    ensure_username_column(conn)

    # ─── 1) Add New User Section ────────────────────────────────────────────────
    st.write("## 1) Add New User")

    # Callback to clear all "new_" session_state keys and rerun
    def clear_new_user_fields():
        keys = [
            "new_first_name",
            "new_last_name",
            "new_gender",
            "new_account_type",
            "new_mobile",
            "new_email",
            "new_password",
            "new_user_groups",
            # we used a disabled text_input for new_username with key "new_username"
            "new_username",
        ]
        for k in keys:
            if k in st.session_state:
                st.session_state.pop(k)
        # Rerun so inputs reset
        st.rerun()

    # Row 1: First Name | Last Name | Gender | Username (auto-generated, disabled)
    col1, col2, col3, col4 = st.columns(4)

    fn = col1.text_input(
        "First Name",
        value=st.session_state.get("new_first_name", ""),
        key="new_first_name"
    )
    ln = col2.text_input(
        "Last Name",
        value=st.session_state.get("new_last_name", ""),
        key="new_last_name"
    )

    gender_options = ["Male", "Female", "Other"]
    default_gender = st.session_state.get("new_gender", "")
    # If default not in options, fallback to first
    if default_gender not in gender_options:
        default_gender = ""
    # Determine index: allow empty selection? In selectbox, we want one of the options.
    # If new_gender not set, default to first "Male"
    try:
        idxg = gender_options.index(default_gender) if default_gender else 0
    except Exception:
        idxg = 0
    gender = col3.selectbox(
        "Gender",
        gender_options,
        index=idxg,
        key="new_gender"
    )

    # Auto-generate username from fn + first 2 letters of ln, lowercased
    username_val = ""
    if fn and ln:
        try:
            username_val = generate_username(fn.strip(), ln.strip())
        except Exception:
            # fallback: firstname + first 2 letters of lastname, lowercased
            username_val = (fn.strip() + ln.strip()[:2]).lower()
    # Display in disabled text_input. Use key so that clear can pop it.
    col4.text_input(
        "Username (auto-generated)",
        value=username_val,
        disabled=True,
        key="new_username"
    )

    # Row 2: Account Type | Mobile (optional) | Email (optional) | Password
    col5, col6, col7, col8 = st.columns(4)
    acct_types = ["Athlete", "Coach", "Admin"]
    default_at = st.session_state.get("new_account_type", "Athlete")
    if default_at not in acct_types:
        default_at = "Athlete"
    try:
        idx_at = acct_types.index(default_at)
    except Exception:
        idx_at = 0
    account_type = col5.radio(
        "Account Type",
        acct_types,
        index=idx_at,
        horizontal=True,
        key="new_account_type"
    )

    mobile = col6.text_input(
        "Mobile (optional)",
        value=st.session_state.get("new_mobile", ""),
        key="new_mobile"
    )
    email = col7.text_input(
        "Email (optional)",
        value=st.session_state.get("new_email", ""),
        key="new_email"
    )
    password = col8.text_input(
        "Password",
        type="password",
        value=st.session_state.get("new_password", ""),
        key="new_password"
    )

    # Row 3: Assign Groups multi-select
    df_groups = fetch_all_groups(conn)  # DataFrame with columns ["id","group_parent","club","group_name","group_sub"]
    group_display_map = {}
    group_options = []
    for _, row in df_groups.iterrows():
        gid = row["id"]
        parts = []
        if row["group_parent"]:
            parts.append(row["group_parent"])
        if row["club"]:
            parts.append(row["club"])
        if row["group_name"]:
            parts.append(row["group_name"])
        if row["group_sub"]:
            parts.append(row["group_sub"])
        label = " / ".join(parts) if parts else f"(ID:{gid})"
        display = f"{label} (ID: {gid})"
        group_display_map[display] = gid
        group_options.append(display)

    if group_options:
        selected_groups = st.multiselect(
            "Assign Groups (coach or athlete may belong to multiple groups)",
            options=group_options,
            default=st.session_state.get("new_user_groups", []),
            key="new_user_groups"
        )
    else:
        st.info("No groups defined yet. Please add groups below before assigning.")
        selected_groups = []

    # Row 4: Buttons: Add User | Clear Fields
    bcol1, bcol2 = st.columns([1, 1])
    with bcol2:
        # Use on_click callback to clear fields
        st.button("Clear Fields", key="clear_new_user", on_click=clear_new_user_fields)
    with bcol1:
        if st.button("Add User", key="add_user_btn"):
            # Validate required: First & Last. Username auto-generated; we verify username_val non-empty.
            if not fn.strip() or not ln.strip():
                st.error("First Name and Last Name are required.")
            else:
                if not username_val:
                    st.error("Username could not be generated. Please ensure First and Last Name are provided.")
                else:
                    try:
                        new_id = generate_client_id(conn)
                        # Insert into clients
                        cursor.execute("""
                            INSERT INTO clients(
                                id, account_type, first_name, last_name,
                                username, gender, mobile, email, password, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            new_id,
                            account_type,
                            fn.strip(),
                            ln.strip(),
                            username_val.strip(),
                            gender if gender else None,
                            mobile.strip() if mobile and mobile.strip() else None,
                            email.strip() if email and email.strip() else None,
                            password if password else None,
                            "active"
                        ))
                        conn.commit()
                        # Assign to selected groups
                        sel_ids = [group_display_map[disp] for disp in selected_groups]
                        assign_user_to_groups(conn, new_id, sel_ids)
                        # Create directories
                        os.makedirs(PDF_DIR / f"{ln.strip()}_{fn.strip()}_{new_id}", exist_ok=True)
                        os.makedirs(PATIENT_STATUS_DIR / f"{ln.strip()}_{fn.strip()}_{new_id}", exist_ok=True)
                        st.success(f"User {fn.strip()} {ln.strip()} added successfully with ID {new_id}!")
                        # Clear fields after add
                        clear_new_user_fields()
                        return  # exit this block
                    except sqlite3.IntegrityError as ie:
                        st.error(f"Error adding user (possible duplicate username/email?): {ie}")
                    except Exception as e:
                        st.error(f"Unexpected error adding user: {e}")

    # ─── 2) Manage Users List & Edit ─────────────────────────────────────────────
    st.markdown("---")
    st.write("## 2) Manage Users")

    all_clients = fetch_all_clients_basic(conn)
    # Build DataFrame for display. Expected tuple format:
    # fetch_all_clients_basic returns tuples like:
    # (id, account_type, first_name, last_name, username, gender, mobile, email, password, status)
    df_clients = pd.DataFrame(all_clients, columns=[
        "ID","Account Type","First Name","Last Name","Username","Gender","Mobile","Email","Password","Status"
    ])
    # Drop password column before display
    if "Password" in df_clients.columns:
        df_clients = df_clients.drop(columns=["Password"])
    # Limit to 15 rows height, allow scrolling
    st.dataframe(df_clients, use_container_width=True, height=400)

    st.write("### Edit User")
    user_opts = [""] + [f"{c[2]} {c[3]} (ID: {c[0]})" for c in all_clients]
    sel = st.selectbox("Select User to Edit", user_opts, key="edit_user_select")
    if sel:
        uid = sel.split("(ID: ")[1].rstrip(")")
        # Find the tuple
        user = next((c for c in all_clients if c[0] == uid), None)
        if user:
            # Unpack user tuple:
            # (id, account_type, first_name, last_name, username, gender, mobile, email, password, status)
            _, uacct, ufn, uln, uusername, ugender, umobile, uemail, upwd, ustatus = user

            # Row 1: Username | First Name | Last Name | Gender
            c1, c2, c3, c4 = st.columns(4)
            eusername = c1.text_input("Username", value=(uusername or ""), key="edit_username")
            efn = c2.text_input("First Name", value=ufn or "", key="edit_fn")
            eln = c3.text_input("Last Name", value=uln or "", key="edit_ln")
            gender_options = ["Male", "Female", "Other"]
            selected_gender_index = gender_options.index(ugender) if ugender in gender_options else 0
            egender = c4.selectbox("Gender", gender_options, index=selected_gender_index, key="edit_gender")

            # Row 2: Account Type | Mobile | Email | Active checkbox
            c5, c6, c7, c8 = st.columns(4)
            acct_types = ["Athlete", "Coach", "Admin"]
            idxat = acct_types.index(uacct) if uacct in acct_types else 0
            eat = c5.radio("Account Type", acct_types, index=idxat, horizontal=True, key="edit_account_type")
            emobile = c6.text_input("Mobile", value=(umobile or ""), key="edit_mobile")
            eemail  = c7.text_input("Email", value=(uemail or ""), key="edit_email")
            estatus = c8.checkbox("Active", value=(ustatus == "active"), key="edit_status")

            # Row 3: Assign Groups multi-select
            st.write("Assign Groups:")
            df_groups2 = fetch_all_groups(conn)
            group_display_map2 = {}
            group_options2 = []
            for _, grow in df_groups2.iterrows():
                gid = grow["id"]
                parts = []
                if grow["group_parent"]:
                    parts.append(grow["group_parent"])
                if grow["club"]:
                    parts.append(grow["club"])
                if grow["group_name"]:
                    parts.append(grow["group_name"])
                if grow["group_sub"]:
                    parts.append(grow["group_sub"])
                label = " / ".join(parts) if parts else f"(ID:{gid})"
                display = f"{label} (ID: {gid})"
                group_display_map2[display] = gid
                group_options2.append(display)
            try:
                current_group_ids = fetch_user_groups(conn, uid)
            except Exception:
                current_group_ids = []
            default_sel = [disp for disp, gid in group_display_map2.items() if gid in current_group_ids]
            sel_groups_edit = st.multiselect(
                "Select Groups",
                options=group_options2,
                default=default_sel,
                key="edit_user_groups"
            )

            # Row 4: Update / Delete
            col_upd, col_del = st.columns([1, 1])
            if col_upd.button("Update User", key="update_user_btn"):
                # Validation
                if not efn.strip() or not eln.strip():
                    st.error("First Name and Last Name are required.")
                elif not eusername.strip():
                    st.error("Username is required.")
                else:
                    try:
                        new_status = "active" if estatus else "deactivated"
                        cursor.execute("""
                            UPDATE clients
                            SET first_name=?, last_name=?, username=?, gender=?, account_type=?, mobile=?, email=?, status=?
                            WHERE id=?
                        """, (
                            efn.strip(),
                            eln.strip(),
                            eusername.strip(),
                            egender if egender else None,
                            eat,
                            emobile.strip() if emobile and emobile.strip() else None,
                            eemail.strip() if eemail and eemail.strip() else None,
                            new_status,
                            uid
                        ))
                        conn.commit()
                        # Update group assignments
                        selected_ids2 = [group_display_map2[x] for x in sel_groups_edit]
                        assign_user_to_groups(conn, uid, selected_ids2)
                        st.success(f"User {efn.strip()} {eln.strip()} updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating user: {e}")

            # Delete with confirmation
            confirm_key = f"confirm_delete_{uid}"
            delete_key = f"delete_user_{uid}"
            confirm = col_del.checkbox("Confirm deletion", key=confirm_key)
            if confirm:
                if col_del.button("Delete User", key=delete_key):
                    try:
                        # Optionally remove user directories
                        dir1 = PDF_DIR / f"{uln}_{ufn}_{uid}"
                        dir2 = PATIENT_STATUS_DIR / f"{uln}_{ufn}_{uid}"
                        for d in [dir1, dir2]:
                            if d.exists() and d.is_dir():
                                try:
                                    shutil.rmtree(d)
                                except Exception:
                                    pass
                        # Delete user row
                        cursor.execute("DELETE FROM clients WHERE id=?", (uid,))
                        conn.commit()
                        st.success(f"User {ufn} {uln} (ID: {uid}) deleted.")
                        # Clear selection and rerun
                        st.session_state.pop("edit_user_select", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting user: {e}")
            else:
                st.write("")  # placeholder

    # ─── 3) Add New Group Section ───────────────────────────────────────────────
    st.markdown("---")
    st.write("## 3) Add New Group")
    gcol1, gcol2, gcol3, gcol4 = st.columns(4)
    # Group Parent dropdown + optional text if "Other"
    gp_sel = gcol1.selectbox("Group Parent", options=GROUP_PARENT_OPTIONS, index=0, key="new_gp_parent_sel")
    if gp_sel == "Other":
        gp_parent = gcol1.text_input("Specify Group Parent", key="new_gp_parent_other").strip()
    else:
        gp_parent = gp_sel

    club = gcol2.text_input("Club", key="new_gp_club")
    group_name = gcol3.text_input("Group Name", key="new_gp_name")
    group_sub  = gcol4.text_input("Group Sub", key="new_gp_sub")

    if st.button("Add Group", key="add_group_row_btn"):
        if not group_name.strip():
            st.error("Group Name is required.")
        else:
            try:
                insert_group_row(
                    conn,
                    group_parent=gp_parent if gp_parent else None,
                    club=club.strip() if club and club.strip() else None,
                    group_name=group_name.strip(),
                    group_sub=group_sub.strip() if group_sub and group_sub.strip() else None
                )
                st.success("Group row added.")
                # Clear inputs
                for k in ["new_gp_parent_sel", "new_gp_parent_other", "new_gp_club", "new_gp_name", "new_gp_sub"]:
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                st.error(f"Error adding group row: {e}")

    # ─── 4) Manage Groups Section ───────────────────────────────────────────────
    st.markdown("---")
    st.write("## 4) Manage Groups")
    df_groups_all = fetch_all_groups(conn)
    if df_groups_all.empty:
        st.info("No groups defined yet.")
    else:
        rows = []
        for _, grow in df_groups_all.iterrows():
            gid = grow["id"]
            gp = grow["group_parent"] or ""
            club = grow["club"] or ""
            gname = grow["group_name"] or ""
            gsub = grow["group_sub"] or ""
            # Fetch assigned Coaches
            cursor.execute("""
                SELECT first_name || ' ' || last_name
                FROM clients JOIN user_group_assignments uga
                  ON clients.id = uga.user_id
                WHERE uga.group_id = ? AND account_type='Coach'
            """, (gid,))
            coaches = [r[0] for r in cursor.fetchall()]
            # Fetch assigned Athletes
            cursor.execute("""
                SELECT first_name || ' ' || last_name
                FROM clients JOIN user_group_assignments uga
                  ON clients.id = uga.user_id
                WHERE uga.group_id = ? AND account_type='Athlete'
            """, (gid,))
            athletes = [r[0] for r in cursor.fetchall()]
            rows.append({
                "ID": gid,
                "Group Parent": gp,
                "Club": club,
                "Group Name": gname,
                "Group Sub": gsub,
                "Coaches": ", ".join(coaches) if coaches else "",
                "Athletes": ", ".join(athletes) if athletes else "",
            })
        df_display = pd.DataFrame(rows, columns=[
            "ID","Group Parent","Club","Group Name","Group Sub","Coaches","Athletes"
        ])
        # Limit height to allow scrolling
        st.dataframe(df_display, use_container_width=True, height=350)

    # Edit/Delete Existing Group
    st.write("### Edit Group")
    edit_map = {}
    edit_opts = []
    for _, grow in df_groups_all.iterrows():
        gid = grow["id"]
        parts = []
        if grow["group_parent"]:
            parts.append(grow["group_parent"])
        if grow["club"]:
            parts.append(grow["club"])
        if grow["group_name"]:
            parts.append(grow["group_name"])
        if grow["group_sub"]:
            parts.append(grow["group_sub"])
        label = " / ".join(parts) if parts else f"(ID:{gid})"
        display = f"{label} (ID: {gid})"
        edit_map[display] = gid
        edit_opts.append(display)
    sel_edit = st.selectbox("Select group to edit", [""] + edit_opts, key="edit_group_select")
    if sel_edit:
        sel_gid = edit_map.get(sel_edit)
        selected_row = df_groups_all[df_groups_all["id"] == sel_gid].iloc[0]
        ec1, ec2, ec3, ec4 = st.columns(4)
        current_gp = selected_row["group_parent"] or ""
        if current_gp in GROUP_PARENT_OPTIONS:
            idxgp = GROUP_PARENT_OPTIONS.index(current_gp)
            new_gp_sel = ec1.selectbox("Group Parent", GROUP_PARENT_OPTIONS, index=idxgp, key="edit_gp_parent_sel")
            new_gp_val = None
        else:
            new_gp_sel = ec1.selectbox("Group Parent", GROUP_PARENT_OPTIONS, index=len(GROUP_PARENT_OPTIONS)-1, key="edit_gp_parent_sel")
            new_gp_val = ec1.text_input("Specify Group Parent", value=current_gp, key="edit_gp_parent_other")
        if new_gp_sel == "Other":
            gp_parent_new = new_gp_val.strip() if new_gp_val else ""
        else:
            gp_parent_new = new_gp_sel

        club_new = ec2.text_input("Club", value=selected_row["club"] or "", key="edit_gp_club")
        group_name_new = ec3.text_input("Group Name", value=selected_row["group_name"] or "", key="edit_gp_name")
        group_sub_new  = ec4.text_input("Group Sub", value=selected_row["group_sub"] or "", key="edit_gp_sub")

        dec1, dec2 = st.columns(2)
        if dec1.button("Update This Group", key="update_group_btn"):
            if not group_name_new.strip():
                st.error("Group Name is required.")
            else:
                try:
                    update_group_row(
                        conn,
                        sel_gid,
                        group_parent=gp_parent_new if gp_parent_new else None,
                        club=club_new.strip() if club_new and club_new.strip() else None,
                        group_name=group_name_new.strip(),
                        group_sub=group_sub_new.strip() if group_sub_new and group_sub_new.strip() else None
                    )
                    st.success("Group row updated.")
                    # Clear relevant session_state keys before rerun
                    for k in ["edit_group_select", "edit_gp_parent_sel", "edit_gp_parent_other",
                              "edit_gp_club", "edit_gp_name", "edit_gp_sub"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating group row: {e}")
        if dec2.button("Delete This Group", key="delete_group_btn"):
            try:
                delete_group_row(conn, sel_gid)
                st.success("Group row deleted.")
                st.session_state.pop("edit_group_select", None)
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting group row: {e}")

    # ─── 5) Database Backup Section ─────────────────────────────────────────────
    st.markdown("---")
    st.write("## 5) Database Backup")
    st.info("Creating a backup copies the entire database file to a 'db_backups' folder.")
    if st.button("Create Database Backup", key="create_db_backup_btn"):
        backup_file_path, backup_file_name = create_database_backup()
        if backup_file_path:
            with open(backup_file_path, "rb") as f:
                st.download_button(
                    label="Download Backup File",
                    data=f.read(),
                    file_name=backup_file_name,
                    mime="application/x-sqlite3",
                    key="download_db_backup"
                )
            st.success(f"Backup available for download: {backup_file_name}")

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_settings()
