import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# Paths relative to this utils.py file
BASE_DIR = Path(__file__).parent.parent
CLIENT_DB_PATH = BASE_DIR / 'client_database.db'
EXERCISE_DB_PATH = BASE_DIR / 'exercise_database.csv'

@st.cache_resource
def get_client_db():
    """
    Returns a cached SQLite connection to the client database.
    """
    conn = sqlite3.connect(CLIENT_DB_PATH, check_same_thread=False)
    return conn

@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Loads and returns the exercise database CSV as a pandas DataFrame.
    Uses utf-8 encoding with fall-back to ISO-8859-1.
    """
    try:
        df = pd.read_csv(EXERCISE_DB_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(EXERCISE_DB_PATH, encoding='ISO-8859-1')

    # Basic validation
    if 'body_part' not in df.columns:
        raise ValueError("The 'body_part' column is missing from exercise_database.csv")

    return df
