# streamlit_app/utils.py

import os
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

# Paths relative to this utils.py file
# Path(__file__).parent is 'streamlit_app/'
# Path(__file__).parent.parent is 'your_project_root/'
BASE_DIR = Path(__file__).parent.parent
CLIENT_DB_PATH = BASE_DIR / 'client_database.db'
EXERCISE_DB_PATH = BASE_DIR / 'exercise_database.csv'

def _initialize_db_schema(conn):
    """
    Ensures that the necessary tables exist in the database.
    This function will be called by get_client_db().
    """
    cursor = conn.cursor()

    # Create clients table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            account_type TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            mobile TEXT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
    """)

    # Create user_groups table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL UNIQUE,
            date_created TEXT NOT NULL
        )
    """)

    # Create group_members table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            member_id TEXT,
            role TEXT NOT NULL, -- e.g., 'Coach', 'Athlete'
            PRIMARY KEY (group_id, member_id),
            FOREIGN KEY (group_id) REFERENCES user_groups(group_id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    """)

    conn.commit()


@st.cache_resource
def get_client_db():
    """
    Returns a cached SQLite connection to the client database.
    Initializes the database schema if tables don't exist.
    """
    try:
        conn = sqlite3.connect(CLIENT_DB_PATH, check_same_thread=False)
        _initialize_db_schema(conn) # Ensure schema exists when connection is made
        return conn
    except Exception as e:
        st.error(f"Could not connect to client database at {CLIENT_DB_PATH}: {e}")
        return None


@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Loads and returns the exercise database CSV as a pandas DataFrame.
    Uses utf-8 encoding with fall-back to ISO-8859-1.
    """
    if not EXERCISE_DB_PATH.exists():
        st.error(f"Exercise database CSV not found at: {EXERCISE_DB_PATH}")
        st.stop() # Stop the app if essential data is missing

    try:
        df = pd.read_csv(EXERCISE_DB_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(EXERCISE_DB_PATH, encoding='ISO-8859-1')
    except Exception as e:
        st.error(f"Error reading exercise database CSV: {e}")
        st.stop()

    # Basic validation
    if 'body_part' not in df.columns:
        raise ValueError("The 'body_part' column is missing from exercise_database.csv")

    return df