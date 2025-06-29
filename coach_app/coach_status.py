# coach_app/coach_status.py

import streamlit as st
from pathlib import Path
import json
from datetime import date
import sys, os

# ─── Allow imports from your main streamlit_app ───────────────────────────
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

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, status, ln=True)
        pdf.ln(1)

        # header
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, 8, "Client", border=1)
        pdf.cell(0, 8, "Restrictions & Comments", border=1, ln=True)

        # rows
        pdf.set_font("Arial", "", 12)
        for e in entries:
            pdf.cell(40, 8, e["name"], border=1)
            pdf.multi_cell(150, 8, e["comms"], border=1)
        pdf.ln(4)

        raw = pdf.output(dest="S")
        if isinstance(raw, str):
            # PyFPDF returned a str → encode to latin1
            return raw.encode("latin1")
        else:
            # fpdf2 returned a bytearray → just wrap in bytes
            return bytes(raw)

def render_coach_status(coach_id: int):
    apply_global_css()
    page_header("Coach Dashboard")

    conn = get_client_db()
    if conn is None:
        st.error("Cannot open client database.")
        return

    # build coach's group filter
    df = fetch_all_groups(conn)
    group_map = {"All": None}
    for _, r in df.iterrows():
        gid = r["id"]
        if gid in fetch_user_groups(conn, coach_id):
            parts = [p for p in (r["group_parent"], r["club"], r["group_name"], r["group_sub"]) if p]
            label = " / ".join(parts)
            group_map[f"{label} (ID:{gid})"] = gid

    col1, col2 = st.columns([3,1])
    sel_label = col1.selectbox("Filter by Group", list(group_map.keys()))
    sel_gid    = group_map[sel_label]

    # fetch clients
    cur = conn.cursor()
    cur.execute("""
      SELECT id, first_name, last_name
        FROM clients
       WHERE account_type='Athlete' AND status='active'
       ORDER BY last_name, first_name
    """)
    athletes = cur.fetchall()

    clients = []
    for cid, fn, ln in athletes:
        if sel_gid and sel_gid not in fetch_user_groups(conn, cid):
            continue
        clients.append((cid, fn, ln))

    if not clients:
        st.info("No clients in your assigned groups.")
        return

    # prepare summary & history
    today_str = date.today().strftime("%Y-%m-%d")
    order_map = {"Modified Training":0, "Full Training":1, "Rehab":2, "No Training":3}
    colour_map = {
        "Modified Training":"orange",
        "Full Training":"green",
        "Rehab":"red",
        "No Training":"purple",
    }

    grouped      = {}
    history_map  = {}

    for cid, fn, ln in clients:
        fld = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}" / "status.json"
        data = {}
        if fld.exists():
            try: data = json.loads(fld.read_text("utf-8"))
            except: data = {}

        curr = data.get("current_status", "Full Training")
        comm = data.get("restrictions", "")
        last = data.get("last_updated", today_str)

        grouped.setdefault(curr, []).append({
            "name": f"{fn} {ln}",
            "comms": comm,
            "last": last
        })

        hist = data.get("history", []) or [{"status":curr,"date":today_str,"comment":comm}]
        for e in hist: e.setdefault("comment","")
        history_map[cid] = hist

    # build PDF
    status_order = sorted(order_map.keys(), key=lambda s: order_map[s])
    pdf_bytes = build_pdf_by_status(
        logo_path=STREAMLIT_APP/"images"/"company_logo4.png",
        heading="Coach Dashboard",
        subheading=f"Group: {sel_label}",
        grouped=grouped,
        status_order=status_order
    )
    col2.download_button(
        "Export PDF", data=pdf_bytes,
        file_name="coach_dashboard.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    # summary merged‐row table
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
      <tr>
        <th>Status</th><th>Client</th>
        <th>Restrictions & Comments</th><th>Last Updated</th>
      </tr>
    """
    for status, rows in sorted(grouped.items(), key=lambda x: order_map[x[0]]):
        clr     = colour_map.get(status, "gray")
        rowspan = len(rows)
        first   = rows[0]
        html += (
            f"<tr>"
              f"<td rowspan='{rowspan}' style='text-align:center;'>{status}</td>"
              f"<td><span style='color:{clr};font-size:24px;'>●</span> {first['name']}</td>"
              f"<td>{first['comms']}</td>"
              f"<td>{first['last']}</td>"
            "</tr>"
        )
        for r in rows[1:]:
            html += (
              "<tr>"
                f"<td><span style='color:{clr};font-size:24px;'>●</span> {r['name']}</td>"
                f"<td>{r['comms']}</td>"
                f"<td>{r['last']}</td>"
              "</tr>"
            )
    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)

    # subheading + separator
    st.markdown("#### Update status details")
    st.write("---")

    # per‐client expanders: timeline + **static** history table
    for cid, fn, ln in clients:
        hist    = history_map[cid]
        fld     = PATIENT_STATUS_DIR / f"{ln}_{fn}_{cid}" / "status.json"
        data    = {}
        if fld.exists():
            try: data = json.loads(fld.read_text("utf-8"))
            except: data = {}

        current = data.get("current_status", "Full Training")
        name    = f"{fn} {ln}"

        with st.expander(name):
            # date markers above bar
            dates    = [date.fromisoformat(h["date"]) for h in hist]
            start_lbl = dates[0].strftime("%Y-%m-%d")
            end_lbl   = date.today().strftime("%Y-%m-%d")
            st.markdown(
                f"""<div style="
                    display:flex;justify-content:space-between;
                    font-size:10px;margin:0 0 4px 0;
                  "><span>{start_lbl}</span><span>{end_lbl}</span></div>""",
                unsafe_allow_html=True
            )

            # timeline bar
            segments = []
            total    = sum(
                max((dates[i+1] - dates[i]).days,1) if i+1 < len(dates)
                else max((date.today() - dates[i]).days,1)
                for i in range(len(dates))
            ) or 1

            for i, h in enumerate(hist):
                start = dates[i]
                end   = dates[i+1] if i+1 < len(dates) else date.today()
                span  = max((end - start).days,1)
                col   = colour_map.get(h["status"], "gray")
                segments.append(f"<div style='flex:{span};background:{col};'></div>")

            st.markdown(
                "<div style='display:flex;width:100%;height:12px;"
                "border:1px solid #444;border-radius:4px;overflow:hidden;"
                "margin:0 0 6px 0;'>"
                + "".join(segments) +
                "</div>",
                unsafe_allow_html=True
            )

            # static history table
            tbl = """
            <style>
              .hist_tbl th{background:#222;color:#fff;}
            </style>
            <table class="hist_tbl" style="width:100%;border-collapse:collapse;font-size:13px">
              <colgroup>
                <col style="width:15%"/><col style="width:15%"/><col style="width:70%"/>
              </colgroup>
              <tr>
                <th>Date</th><th>Status</th><th>Comments</th>
              </tr>
            """
            for entry in hist:
                d = entry["date"]
                s = entry["status"]
                c = entry.get("comment","")
                color = colour_map.get(s,"gray")
                tbl += (
                  "<tr>"
                    f"<td style='border:1px solid #444;padding:4px'>{d}</td>"
                    f"<td style='border:1px solid #444;padding:4px;color:{color}'>{s}</td>"
                    f"<td style='border:1px solid #444;padding:4px'>{c}</td>"
                  "</tr>"
                )
            tbl += "</table>"
            st.markdown(tbl, unsafe_allow_html=True)

    st.info("Use the group filter above or expand a client to view full history.")


if __name__ == "__main__":
    render_coach_status(coach_id=1)
