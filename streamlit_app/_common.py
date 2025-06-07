# streamlit_app/_common.py

import streamlit as st
import base64
from pathlib import Path

def apply_global_css():
    """
    Inject CSS for:
      - Full-width primary buttons (sidebar & page)
      - Sidebar padding & footer
      - TextArea font sizing
      - Hiding the default Streamlit page menu (if you want)
    Call once, as early as possible (e.g. in index.py).
    """
    st.markdown(
        """
        <style>
        /* ============ PRIMARY BUTTON STYLE ============ */
        :root { --primary-color: #4169e1; }
        .stButton>button {
            width: 100% !important;
            background-color: var(--primary-color) !important;
            border: 1px solid var(--primary-color) !important;
            border-radius: 5px !important;
            color: #fff !important;
            padding: 0.75em 1em !important;
            font-size: 1rem !important;
            cursor: pointer !important;
            transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out !important;
        }
        .stButton>button:hover {
            background-color: #1DA1F2 !important;
            border-color: #1DA1F2 !important;
        }
        .stButton>button:active {
            background-color: #00FFFF !important;
            border-color: #00FFFF !important;
        }

        /* ============ SIDEBAR LAYOUT ============ */
        .stSidebar .css-1d391kg {
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        .sidebar-footer {
            text-align: center;
            font-size: small;
            font-style: italic;
            color: #888;
            padding-top: 2rem;
        }

        /* ============ TEXTAREAS ============ */
        .stTextArea label {
            font-size: 1.2rem !important;
        }
        .stTextArea textarea {
            font-size: 1.2rem !important;
        }

        /* ============ HIDE DEFAULT PAGE MENU ============ */
        [data-testid="page-menu"] { display: none !important; }

        /* limit & center the logo in the sidebar */
        .stSidebar img {
          max-width: 80% !important;
          height: auto !important;
          display: block !important;
          margin: 0 auto !important;
          }
          
        /* Reduce the gap above the page content */
        .block-container {
          padding-top: 0.85rem !important;
          }

         </style>
        """,
        unsafe_allow_html=True,
    )


def get_base64_image(image_path: Path) -> str:
    """
    Read a local image and return its base64 blob.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")
    data = img_path.read_bytes()
    return base64.b64encode(data).decode()


def page_header(title: str, icon_path: Path = None):
    """
    Render a header with:
      [icon] Title                             [company logo]
    followed by a horizontal rule.
    """
    root = Path(__file__).parent                     # streamlit_app/
    logo_file = root / "images" / "company_logo4.png"
    logo_b64 = get_base64_image(logo_file) if logo_file.exists() else ""

    icon_html = ""
    if icon_path:
        ip = Path(icon_path)
        if ip.exists():
            icon_b64 = get_base64_image(ip)
            icon_html = (
                f'<img src="data:image/png;base64,{icon_b64}" '
                f'style="width:50px; margin-right:10px;">'
            )

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center;">
            {icon_html}
            <h1 style="margin:0;">{title}</h1>
          </div>
          <div>
            <img src="data:image/png;base64,{logo_b64}" style="width:150px;">
          </div>
        </div>
        <hr style="margin-top:10px;">
        """,
        unsafe_allow_html=True,
    )


def get_status_color(status: str) -> str:
    """
    Map a client status string to a hex color.
    Used in Client Status page.
    """
    mapping = {
        "Full Training":     "#28a745",
        "Modified Training": "#ffc107",
        "Rehab":             "#17a2b8",
        "No Training":       "#dc3545",
    }
    return mapping.get(status, "#777777")
