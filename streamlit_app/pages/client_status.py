import streamlit as st
from pathlib import Path
import sqlite3, json
import pandas as pd
from datetime import datetime

from _common import apply_global_css, page_header

# ──────────────────────────────────────────────────────────────────────────────
# Adjust these to match your layout
BASE_DIR           = Path(__file__).parent.parent
PATIENT_STATUS_DIR = BASE_DIR / "patient_status"
USER_GROUPS_DB     = BASE_DIR / "user_groups.db"
# ──────────────────────────────────────────────────────────────────────────────

def load_patient_statuses() -> pd.DataFrame:
    """Read every patient’s status.json into a single DataFrame."""
    records = []
    for folder in PATIENT_STATUS_DIR.iterdir():
        if not folder.is_dir() or folder.name == "archived_clients":
            continue
        status_file = folder / "status.json"
        if not status_file.exists():
            continue
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
            data["_status_path"] = status_file  # remember where to write back
            records.append(data)
        except Exception:
            continue
    return pd.DataFrame(records)

def load_user_groups() -> dict[str, list[str]]:
    """Returns mapping group_name → list of client_ids."""
    if not USER_GROUPS_DB.exists():
        return {}
    mapping: dict[str, list[str]] = {}
    try:
        with sqlite3.connect(USER_GROUPS_DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT group_id, group_name FROM user_groups")
            for gid, name in cur.fetchall():
                cur.execute(
                    "SELECT member_id FROM group_members WHERE group_id=?",
                    (gid,)
                )
                members = [row[0] for row in cur.fetchall()]
                mapping[name] = members
    except sqlite3.OperationalError:
        # tables haven’t been created yet
        return {}
    return mapping

def save_status(row, new_status):
    """Overwrite the patient’s status.json with updated status."""
    path: Path = row["_status_path"]
    payload = dict(row)
    payload["current_status"] = new_status
    payload["last_updated"]   = datetime.today().strftime("%Y-%m-%d")
    # drop our helper column before saving
    payload.pop("_status_path", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st.success(f"{payload['firstname']} {payload['lastname']}: status updated to {new_status}")

def render_client_status():
    apply_global_css()
    page_header("Client Status")

    df = load_patient_statuses()
    if df.empty:
        st.warning("No client status data found.  Have you run at least one session?")
        return

    groups = load_user_groups()
    if groups:
        options = ["All"] + sorted(groups.keys())
        sel = st.selectbox("Filter by Group", options)
        if sel != "All":
            allowed = set(groups[sel])
            df = df[df["client_id"].isin(allowed)]
            if df.empty:
                st.info("No clients in that group.")
                return
    else:
        st.info("No groups defined yet.  Head to Settings → User Groups to add one.")
        sel = "All"

    # build a form per row
    status_choices = ["Rehab","Modified Training","No Training","Full Training"]
    for idx, row in df.reset_index(drop=True).iterrows():
        name = f"{row['firstname']} {row['lastname']}"

        with st.expander(name, expanded=False):
            st.markdown(f"- **Group(s):** {row.get('group','N/A')}")
            st.markdown(f"- **Previous status:** {row.get('current_status','N/A')}")
            st.markdown(f"- **Last updated:** {row.get('last_updated','N/A')}")
            new = st.selectbox(
                "Select new status",
                status_choices,
                index=status_choices.index(row.get("current_status","Rehab"))
            )
            if st.button("Save Status", key=f"save_{row['client_id']}"):
                save_status(row, new)

    st.info("Pick a client above to update their status.")

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_client_status()
