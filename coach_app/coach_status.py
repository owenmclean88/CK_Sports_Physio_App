# coach_app/coach_status.py

import streamlit as st
from pathlib import Path
import json
from datetime import date
import sys, os

# allow imports from your main “streamlit_app” folder
ROOT = Path(__file__).parent.parent
STREAMLIT_APP = ROOT / "streamlit_app"
sys.path.insert(0, str(STREAMLIT_APP))

from utils               import get_client_db, fetch_all_groups, fetch_user_groups
from _common             import apply_global_css, page_header
from pages.client_status import PATIENT_STATUS_DIR
from fpdf import FPDF

def build_pdf_by_status(logo_path: Path, heading: str, subheading: str,
                        grouped: dict[str, list[dict]], status_order: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # logo top-right
    if logo_path.exists():
        pdf.image(str(logo_path), x=170, y=8, w=30)
    pdf.ln(20)

    # main heading
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, heading, ln=True)
    # subheading
    pdf.set_font("Arial", "", 14)
    pdf.cell(0, 8, subheading, ln=True)
    pdf.ln(5)

    # one table per status
    for status in status_order:
        entries = grouped.get(status, [])
        if not entries:
            continue

        # status title
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, status, ln=True)
        pdf.ln(1)

        # column headers
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, 8, "Client", border=1)
        pdf.cell(150, 8, "Restrictions & Comments", border=1, ln=True)

        # rows
        pdf.set_font("Arial", "", 12)
        for e in entries:
            pdf.cell(40, 8, e["name"], border=1)
            pdf.multi_cell(150, 8, e["comms"], border=1)
        pdf.ln(4)

    return pdf.output(dest="S").encode("latin1")


def render_coach_status(coach_id: int):
    apply_global_css()
    page_header("Coach Dashboard")

    # DB connection
    conn = get_client_db()
    if conn is None:
        st.error("Cannot open client database.")
        return

    # fetch this coach's groups
    df = fetch_all_groups(conn)
    group_map: dict[str, int|None] = {"All": None}
    for _, r in df.iterrows():
        gid = r["id"]
        if gid in fetch_user_groups(conn, coach_id):
            parts = [p for p in (r["group_parent"], r["club"], r["group_name"], r["group_sub"]) if p]
            label = " / ".join(parts)
            group_map[f"{label} (ID:{gid})"] = gid

    # dropdown + export button side by side
    col1, col2 = st.columns([3,1])
    sel_label = col1.selectbox("Filter by Group", list(group_map.keys()), index=0)
    sel_gid    = group_map[sel_label]

    # prepare for PDF
    today_str   = date.today().strftime("%Y-%m-%d")
    order_map   = {"Modified Training":0, "Full Training":1, "Rehab":2, "No Training":3}
    colour_map  = {"Modified Training":"orange","Full Training":"green","Rehab":"red","No Training":"purple"}
    grouped     = {}   # status → list of {name, comms, last}
    history_map = {}   # cid → history list

    # fetch athletes
    cur = conn.cursor()
    cur.execute("""
      SELECT id, first_name, last_name
        FROM clients
       WHERE account_type='Athlete' AND status='active'
       ORDER BY last_name, first_name
    """)
    athletes = cur.fetchall()

    # build grouped + history_map
    for cid, fn, ln in athletes:
        if sel_gid and sel_gid not in fetch_user_groups(conn, cid):
            continue

        fld = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}" / "status.json"
        data = {}
        if fld.exists():
            try: data = json.loads(fld.read_text("utf-8"))
            except: data = {}

        curr = data.get("current_status", "Full Training")
        comm = data.get("restrictions", "")
        last = data.get("last_updated", today_str)
        grouped.setdefault(curr, []).append({"name":f"{fn} {ln}", "comms":comm, "last":last})

        hist = data.get("history", []) or [{"status":curr,"date":today_str,"comment":comm}]
        for e in hist: e.setdefault("comment", "")
        history_map[cid] = hist

    # build & show PDF download
    status_order = sorted(order_map.keys(), key=lambda s: order_map[s])
    pdf_bytes = build_pdf_by_status(
        logo_path=STREAMLIT_APP/"images"/"company_logo4.png",
        heading="Coach Dashboard",
        subheading=f"Group: {sel_label}",
        grouped=grouped,
        status_order=status_order
    )
    col2.download_button(
        "Export PDF",
        data=pdf_bytes,
        file_name="coach_dashboard.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    # summary merged-row table
    html = """
    <style>
      .tbl{width:100%;border-collapse:collapse;}
      .tbl th,.tbl td{border:1px solid #444;padding:8px;vertical-align:top;}
      .tbl th{background:#222;color:#fff;}
    </style>
    <table class="tbl">
      <colgroup>
        <col style="width:8%"/><col style="width:17%"/>
        <col style="width:60%"/><col style="width:15%"/>
      </colgroup>
      <tr><th>Status</th><th>Client</th><th>Restrictions & Comments</th><th>Last Updated</th></tr>
    """
    for status, rows in sorted(grouped.items(), key=lambda x: order_map[x[0]]):
        clr = colour_map.get(status, "gray")
        rowspan = len(rows)
        first = rows[0]
        html += (
            f"<tr>"
            f"<td rowspan='{rowspan}' style='text-align:center;'>{status}</td>"
            f"<td><span style='color:{clr};font-size:24px;'>●</span> {first['name']}</td>"
            f"<td>{first['comms']}</td>"
            f"<td>{first['last']}</td>"
            f"</tr>"
        )
        for r in rows[1:]:
            html += (
                "<tr>"
                f"<td><span style='color:{clr};font-size:24px;'>●</span> {r['name']}</td>"
                f"<td>{r['comms']}</td>"
                f"<td>{r['last']}</td>"
                f"</tr>"
            )
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # subheading + separator
    st.markdown("#### Update status details")
    st.write("---")

    # expanders with timeline + history editor
    for cid, fn, ln in athletes:
        if sel_gid and sel_gid not in fetch_user_groups(conn, cid):
            continue

        hist    = history_map[cid]
        data    = {}
        fld     = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}" / "status.json"
        if fld.exists():
            try: data = json.loads(fld.read_text("utf-8"))
            except: data = {}
        current = data.get("current_status", "Full Training")
        name    = f"{fn} {ln}"

        with st.expander(name):
            # 1) headers row (tight)
            cols = st.columns([2,2,6,1])
            cols[0].write("Status")
            cols[1].write("Date")
            cols[2].write("Restrictions & Comments")

            # 2) each history entry
            for i, entry in enumerate(list(hist)):
                row = st.columns([2,2,6,1])
                # bullet + status
                clr = colour_map.get(entry["status"], "gray")
                row[0].markdown(
                    f"<span style='color:{clr};font-size:24px;'>●</span> {entry['status']}",
                    unsafe_allow_html=True
                )
                # date input
                dval = date.fromisoformat(entry["date"])
                newd = row[1].date_input("", value=dval, key=f"hist_date_{cid}_{i}")
                entry["date"] = newd.strftime("%Y-%m-%d")
                # comment input
                newc = row[2].text_input("", value=entry["comment"], key=f"hist_comment_{cid}_{i}")
                entry["comment"] = newc
                # clear
                if row[3].button("Clear", key=f"hist_clear_{cid}_{i}"):
                    hist.pop(i)
                    # persist clear (same logic as before)…
                    last_e = hist[-1] if hist else {"status":"Full Training","date":today_str,"comment":""}
                    payload = {
                        "firstname": fn,
                        "lastname": ln,
                        "client_id": cid,
                        "current_status": last_e["status"],
                        "restrictions": last_e.get("comment",""),
                        "last_updated": last_e["date"],
                        "history": hist
                    }
                    odir = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}"
                    odir.mkdir(parents=True, exist_ok=True)
                    with open(odir / "status.json", "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2)
                    st.rerun()

            # 3) date labels above bar
            dates    = [date.fromisoformat(h["date"]) for h in hist]
            start_lbl= dates[0].strftime("%Y-%m-%d")
            end_lbl  = date.today().strftime("%Y-%m-%d")
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            font-size:10px;margin:0 0 4px 0;">
                  <span>{start_lbl}</span><span>{end_lbl}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 4) timeline bar
            segs = []
            total_days = sum(
                max((dates[i+1] - dates[i]).days, 1) if i+1 < len(dates)
                else max((date.today() - dates[i]).days, 1)
                for i in range(len(dates))
            ) or 1
            for i, h in enumerate(hist):
                start = dates[i]
                end   = dates[i+1] if i+1 < len(dates) else date.today()
                span  = max((end - start).days, 1)
                col   = colour_map.get(h["status"], "gray")
                segs.append(f"<div style='flex:{span};background:{col};'></div>")

            st.markdown(
                "<div style='display:flex;width:100%;height:12px;"
                "border:1px solid #444;border-radius:4px;overflow:hidden;margin:0 0 6px 0;'>"
                + "".join(segs) +
                "</div>",
                unsafe_allow_html=True,
            )

            # 5) tight “Update New Status” row
            cs, ds, rs = st.columns([3,3,6])
            idx = list(order_map.keys()).index(current)
            new_s = cs.selectbox("Update New Status", list(order_map.keys()), idx, key=f"cs_{cid}")
            new_d = ds.date_input("", value=date.fromisoformat(data.get("last_updated", start_lbl)), key=f"cd_{cid}")
            new_r = rs.text_input("", value=data.get("restrictions",""), key=f"cr_{cid}")

            # 6) Save button
            if st.button("Save Changes", key=f"save_{cid}"):
                nd = new_d.strftime("%Y-%m-%d")
                if not hist or hist[-1]["status"] != new_s:
                    hist.append({"status":new_s,"date":nd,"comment":new_r})
                payload = {
                    "firstname": fn,
                    "lastname": ln,
                    "client_id": cid,
                    "current_status": new_s,
                    "restrictions": new_r,
                    "last_updated": nd,
                    "history": hist
                }
                odir = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}"
                odir.mkdir(parents=True, exist_ok=True)
                with open(odir/"status.json","w",encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                st.success(f"{name}: status updated!")
                st.rerun()

    st.info("Use the group filter above or expand a client to view full history.")


if __name__ == "__main__":
    render_coach_status(coach_id=1)
