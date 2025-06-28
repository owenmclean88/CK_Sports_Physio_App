# streamlit_app/pages/client_status.py

import streamlit as st
from pathlib import Path
import json
from datetime import datetime, date

from _common import apply_global_css, page_header
from utils import get_client_db, fetch_all_groups, fetch_user_groups

# Path to patient_status folder
PATIENT_STATUS_DIR = Path(__file__).parent.parent / "patient_status"


def render_client_status():
    apply_global_css()
    page_header("Client Status")

    conn = get_client_db()
    if conn is None:
        st.error("Cannot access client database.")
        return

    # --- Group filter ---
    df_groups = fetch_all_groups(conn)
    group_map = {"All": None}
    for _, row in df_groups.iterrows():
        gid = row["id"]
        parts = [p for p in (row["group_parent"], row["club"], row["group_name"], row["group_sub"]) if p]
        label = " / ".join(parts)
        group_map[f"{label} (ID:{gid})"] = gid
    sel_group = st.selectbox("Filter by Group", list(group_map.keys()), index=0)

    # --- Fetch clients ---
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, first_name, last_name
          FROM clients
         WHERE account_type='Athlete' AND status='active'
         ORDER BY last_name, first_name
        """
    )
    all_clients = cur.fetchall()

    # --- Apply group filter ---
    clients = []
    if sel_group != "All":
        gid = group_map[sel_group]
        for cid, fn, ln in all_clients:
            if gid in fetch_user_groups(conn, cid):
                clients.append((cid, fn, ln))
    else:
        clients = all_clients

    if not clients:
        st.info("No clients to display.")
        return

    # --- Color & order definitions ---
    order_map = {"Modified Training": 0, "Full Training": 1, "Rehab": 2, "No Training": 3}
    colour_map = {
        "Full Training": "green",
        "Modified Training": "orange",
        "Rehab": "red",
        "No Training": "purple",
    }

    # --- Aggregate and history ---
    grouped = {}
    history_map = {}
    today_str = datetime.today().strftime("%Y-%m-%d")
    for cid, fn, ln in clients:
        name = f"{fn} {ln}"
        folder = f"{ln}_{fn}_{cid}"
        sf = PATIENT_STATUS_DIR / folder / "status.json"
        data = {}
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
            except:
                data = {}
        current = data.get("current_status", "Full Training")
        last_upd = data.get("last_updated", today_str)
        comments = data.get("restrictions", "")
        grouped.setdefault(current, []).append({"cid": cid, "name": name, "last_upd": last_upd, "comments": comments})
        hist = data.get("history", [])
        if not hist:
            hist = [{"status": current, "date": today_str, "comment": comments}]
        for entry in hist:
            entry.setdefault("comment", "")
        history_map[cid] = hist

    sorted_groups = sorted(grouped.items(), key=lambda x: order_map.get(x[0], 99))

    # --- Summary table ---
    table_html = (
        '<style>'
        '.status-table{width:100%;border-collapse:collapse;}'
        '.status-table th, .status-table td{border:1px solid #444;padding:8px;vertical-align:top;}'
        '.status-table th{background:#222;color:#fff;}'
        '</style>'
        '<table class="status-table">'
        '<colgroup>'
        '<col style="width:8%"/>'
        '<col style="width:17%"/>'
        '<col style="width:60%"/>'
        '<col style="width:15%"/>'
        '</colgroup>'
        '<tr><th>Status</th><th>Client</th><th>Restrictions & Comments</th><th>Last Updated</th></tr>'
    )
    for status_text, rows in sorted_groups:
        colour = colour_map.get(status_text, "gray")
        rowspan = len(rows)
        first = rows[0]
        table_html += (
            f'<tr>'
            f'<td rowspan="{rowspan}" style="text-align:center;">{status_text}</td>'
            f'<td><span style="color:{colour};font-size:24px;">●</span> {first["name"]}</td>'
            f'<td>{first["comments"]}</td>'
            f'<td>{first["last_upd"]}</td>'
            '</tr>'
        )
        for r in rows[1:]:
            table_html += (
                '<tr>'
                f'<td><span style="color:{colour};font-size:24px;">●</span> {r["name"]}</td>'
                f'<td>{r["comments"]}</td>'
                f'<td>{r["last_upd"]}</td>'
                '</tr>'
            )
    table_html += '</table>'
    st.markdown(table_html, unsafe_allow_html=True)

    st.write("---")

    # --- Expanders with timeline ---
    for cid, fn, ln in clients:
        name = f"{fn} {ln}"
        hist = history_map[cid]
        folder = f"{ln}_{fn}_{cid}"
        sf = PATIENT_STATUS_DIR / folder / "status.json"
        data = {}
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
            except:
                data = {}
        current = data.get("current_status", "Full Training")

        with st.expander(name):
            st.write("**Edit Status Change History:**")
            cols = st.columns([2,2,6,1])
            cols[0].write("Status"); cols[1].write("Date"); cols[2].write("Restrictions & Comments"); cols[3].write("")
            for i, entry in enumerate(hist.copy()):
                row = st.columns([2,2,6,1])
                # status row
                row[0].markdown(
                    f"<span style='color:{colour_map.get(entry['status'],'gray')};font-size:24px;'>●</span> {entry['status']}",
                    unsafe_allow_html=True
                )
                # date input
                dval = date.fromisoformat(entry['date'])
                newd = row[1].date_input("", value=dval, key=f"hist_date_{cid}_{i}")
                entry['date'] = newd.strftime("%Y-%m-%d")
                # comment input
                newc = row[2].text_input("", value=entry['comment'], key=f"hist_comment_{cid}_{i}")
                entry['comment'] = newc
                # clear button: remove and persist
                if row[3].button("Clear", key=f"remove_{cid}_{i}"):
                    hist.pop(i)
                    # determine new current status
                    if hist:
                        last = hist[-1]
                        new_status = last['status']
                        new_last = last['date']
                        new_rest = last.get('comment','')
                    else:
                        new_status = 'Full Training'
                        new_last = today_str
                        new_rest = ''
                    # save updated JSON
                    payload = {
                        'firstname': fn,
                        'lastname': ln,
                        'client_id': cid,
                        'current_status': new_status,
                        'restrictions': new_rest,
                        'last_updated': new_last,
                        'history': hist
                    }
                    odir = PATIENT_STATUS_DIR / folder
                    odir.mkdir(parents=True, exist_ok=True)
                    with open(odir / 'status.json','w',encoding='utf-8') as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    st.rerun()

            # continuous timeline bar
            dates = [date.fromisoformat(h['date']) for h in hist]
            total_days = sum(
                max((dates[j+1]-dates[j]).days,1) if j+1<len(dates) else max((date.today()-dates[j]).days,1)
                for j in range(len(dates))
            ) or 1
            segments = []
            cum = 0
            markers_html = '<div style="position:relative;width:100%;margin-bottom:4px;">'
            for idx, h in enumerate(hist):
                start = dates[idx]
                end = dates[idx+1] if idx+1<len(dates) else date.today()
                span = max((end-start).days,1)
                col = colour_map.get(h['status'],'gray')
                segments.append(f"<div style='flex:{span};background-color:{col};'></div>")
                if idx>0:
                    left_pct = cum/total_days*100
                    markers_html += (
                        f"<div style='position:absolute;left:{left_pct:.2f}%;top:-10px;font-size:10px;color:#fff;'>{start.strftime('%Y-%m-%d')}</div>"
                    )
                cum += span
            markers_html += '</div>'
            bar_html = '<div style="display:flex;width:100%;height:14px;border:1px solid #444;border-radius:4px;overflow:hidden;">' + ''.join(segments) + '</div>'
            # start/end labels
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;font-size:10px;margin-bottom:2px;'><span>{dates[0].strftime('%Y-%m-%d')}</span><span>{date.today().strftime('%Y-%m-%d')}</span></div>",
                unsafe_allow_html=True
            )
            st.markdown(markers_html + bar_html, unsafe_allow_html=True)

            # current status entry
            st.write("**Current Status & Date:**")
            cs_cols = st.columns([3,3,6])
            sel_idx = list(order_map.keys()).index(current)
            new_s = cs_cols[0].selectbox("", list(order_map.keys()), index=sel_idx, key=f"status_{cid}")
            lval = data.get('last_updated', today_str)
            new_l = cs_cols[1].date_input("", value=date.fromisoformat(lval), key=f"lastupd_{cid}")
            new_r = cs_cols[2].text_input("", value=data.get('restrictions',''), key=f"restrict_{cid}")
            if st.button("Save Changes", key=f"save_{cid}"):
                odir = PATIENT_STATUS_DIR / folder
                odir.mkdir(parents=True, exist_ok=True)
                ls = new_l.strftime('%Y-%m-%d')
                if not hist or hist[-1]['status'] != new_s:
                    hist.append({'status':new_s,'date':ls,'comment':new_r})
                payload = {
                    'firstname': fn,
                    'lastname': ln,
                    'client_id': cid,
                    'current_status': new_s,
                    'restrictions': new_r,
                    'last_updated': ls,
                    'history': hist
                }
                with open(odir / 'status.json','w',encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                st.success(f"{name}: status updated!")
                st.rerun()

    st.info("Use the group filter above or expand clients to edit.")

if __name__ == "__main__":
    render_client_status()
