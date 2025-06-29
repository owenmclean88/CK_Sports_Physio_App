import streamlit as st
from streamlit_app.utils   import get_client_db, fetch_all_groups, fetch_user_groups
from streamlit_app._common import apply_global_css, page_header

def coach_settings():
    apply_global_css()
    page_header("My Account Settings")

    conn = get_client_db()
    if conn is None:
        st.error("Cannot access database.")
        return

    coach_id = st.session_state.get("coach_id")
    if not coach_id:
        st.error("No coach authenticated.")
        return

    cur = conn.cursor()
    cur.execute("""
        SELECT username, first_name, last_name, email
          FROM clients
         WHERE id = ? AND account_type='Coach'
    """, (coach_id,))
    row = cur.fetchone()
    if not row:
        st.error("Coach record not found.")
        return

    username, fn, ln, email = row
    st.text_input("Username", username, disabled=True)
    new_fn = st.text_input("First Name", fn, key="chg_fn")
    new_ln = st.text_input("Last Name", ln, key="chg_ln")
    new_email = st.text_input("Email", email, key="chg_email")

    if st.button("Save Changes"):
        cur.execute("""
            UPDATE clients
               SET first_name=?, last_name=?, email=?
             WHERE id=?
        """, (new_fn, new_ln, new_email, coach_id))
        conn.commit()
        st.success("Profile updated.")
