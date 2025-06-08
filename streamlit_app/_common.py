# streamlit_app/_common.py

import streamlit as st
import base64 # <--- KEPT THIS IMPORT
from pathlib import Path

# NOTE: No import for get_base64_image from utils, as it's defined in this file.

def apply_global_css():
    st.markdown(
        """
        <style>
        :root { --primary-color: #4169e1; }

        /* PRIMARY BUTTONS */
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

        /* SIDEBAR LAYOUT */
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

        /* TEXTAREAS */
        .stTextArea label {
            font-size: 1.2rem !important;
        }
        .stTextArea textarea {
            font-size: 1.2rem !important;
        }

        /* HIDE DEFAULT PAGE MENU */
        [data-testid="page-menu"] { display: none !important; }

        /* SIDEBAR LOGO */
        .stSidebar img {
            max-width: 80% !important;
            height: auto !important;
            display: block !important;
            margin: 0 auto !important;
        }

        /* REDUCE TOP PADDING */
        .block-container {
            padding-top: 0.85rem !important;
        }

        /* CALENDAR NAV BUTTONS */
        .fc .fc-button,
        .fc .fc-button.fc-button-primary {
          background-color: var(--primary-color) !important;
          border: 1px solid var(--primary-color) !important;
          color: #ffffff !important;
          border-radius: 5px !important;
        }
        .fc .fc-button:hover,
        .fc .fc-button.fc-button-primary:hover {
          background-color: #1DA1F2 !important;
          border-color: #1DA1F2 !important;
        }
        .fc .fc-button:disabled,
        .fc .fc-button.fc-button-disabled {
          opacity: 0.5 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# KEPT THIS FUNCTION HERE as requested
def get_base64_image(image_path: Path) -> str:
    """
    Read a local image file and return its base64‐encoded string for embedding.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        # Changed to return a placeholder rather than raising error for robustness
        # This will prevent the app from crashing if an image is missing
        return base64.b64encode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=").decode("utf-8")
    try:
        data = img_path.read_bytes()
        return base64.b64encode(data).decode()
    except Exception as e:
        st.error(f"Error encoding image {image_path}: {e}")
        return base64.b64encode(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=").decode("utf-8")


def page_header(title: str, icon_path: Path = None):
    """
    Render a header with:
      [optional icon]   Title   [company logo on right]
    followed by a horizontal rule.
    """
    root = Path(__file__).parent  # streamlit_app/
    logo_file = root / "images" / "company_logo4.png"
    logo_b64 = get_base64_image(logo_file) # Calls the get_base64_image from THIS file
    
    # Handle missing logo gracefully
    if not logo_file.exists():
        st.warning(f"Company logo not found at: {logo_file}. Using placeholder.")


    icon_html = ""
    if icon_path:
        ip = Path(icon_path)
        if ip.exists():
            icon_b64 = get_base64_image(ip) # Calls the get_base64_image from THIS file
            icon_html = (
                f'<img src="data:image/png;base64,{icon_b64}" '
                f'style="width:50px; margin-right:10px;" />'
            )
        else:
            st.warning(f"Header icon not found at: {ip}")


    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center;">
            {icon_html}<h1 style="margin:0;">{title}</h1>
          </div>
          <div>
            <img src="data:image/png;base64,{logo_b64}" style="width:150px;" />
          </div>
        </div>
        <hr style="margin-top:10px;" />
        """,
        unsafe_allow_html=True,
    )

def get_status_color(status: str) -> str:
    """
    Map a client-status string to a hex color.
    Used on your Client Status page.
    """
    mapping = {
        "Full Training":     "#28a745",   # green
        "Modified Training": "#ffc107",   # amber
        "Rehab":             "#17a2b8",   # teal
        "No Training":       "#dc3545",   # red
    }
    return mapping.get(status, "#777777")   # default grey