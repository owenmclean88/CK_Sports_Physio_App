# streamlit_app/utils.py

import os
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
from datetime import date

# Paths relative to this utils.py file
BASE_DIR = Path(__file__).parent.parent  # project root (parent of streamlit_app)
CLIENT_DB_PATH = BASE_DIR / 'client_database.db'
EXERCISE_DB_PATH = BASE_DIR / 'exercise_database.csv'


def _initialize_db_schema(conn: sqlite3.Connection):
    """
    Ensures that the necessary tables exist in the database, and performs migrations if needed.
    Called when establishing connection.
    """
    cursor = conn.cursor()

    # 1) Create clients table if it doesn't exist, with username and gender columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            account_type TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            username TEXT UNIQUE,    -- new username column
            gender TEXT DEFAULT '',  -- gender column
            mobile TEXT,
            email TEXT UNIQUE,
            password TEXT,
            status TEXT NOT NULL DEFAULT 'active'
        )
    """)
    # Check existing columns and add missing ones if possible:
    cursor.execute("PRAGMA table_info(clients)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if 'username' not in existing_cols:
        try:
            cursor.execute("ALTER TABLE clients ADD COLUMN username TEXT UNIQUE")
        except Exception:
            # SQLite ALTER TABLE may not allow ADD COLUMN with UNIQUE constraint in some versions;
            # if that fails, user may need manual migration.
            pass
    if 'gender' not in existing_cols:
        try:
            cursor.execute("ALTER TABLE clients ADD COLUMN gender TEXT DEFAULT ''")
        except Exception:
            pass

    # 2) Create group_hierarchy table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS group_hierarchy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_parent TEXT,
            club TEXT,
            group_name TEXT NOT NULL,
            group_sub TEXT
        )
    """)

    # 3) Create user_group_assignments table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_group_assignments (
            user_id TEXT,
            group_id INTEGER,
            PRIMARY KEY (user_id, group_id),
            FOREIGN KEY (user_id) REFERENCES clients(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES group_hierarchy(id) ON DELETE CASCADE
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
        # Ensure parent directory exists
        CLIENT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(CLIENT_DB_PATH), check_same_thread=False)
        # Enable foreign keys for cascade deletes
        conn.execute("PRAGMA foreign_keys = ON;")
        _initialize_db_schema(conn)
        return conn
    except Exception as e:
        st.error(f"Could not connect to client database at {CLIENT_DB_PATH}: {e}")
        return None


def generate_client_id(conn: sqlite3.Connection) -> str:
    """
    Generate a random 8-digit ID not already in clients table.
    """
    import random
    cur = conn.cursor()
    while True:
        cid = str(random.randint(10_000_000, 99_999_999))
        cur.execute("SELECT 1 FROM clients WHERE id=?", (cid,))
        if not cur.fetchone():
            return cid


def generate_username(first_name: str, last_name: str) -> str:
    """
    Generate a username from first_name + first 2 letters of last_name.
    Example: "Owen" + "McLean" -> "Owenmc"
    Returns lowercase. Caller can override if desired.
    """
    if not first_name:
        base = ""
    else:
        base = first_name.strip()
    tail = ""
    if last_name and len(last_name.strip()) >= 2:
        tail = last_name.strip()[:2]
    elif last_name:
        tail = last_name.strip()
    username = (base + tail).lower()
    # Optionally, one could check uniqueness here, but typically we set and then conflict is handled upstream.
    return username


def fetch_all_clients_basic(conn: sqlite3.Connection):
    """
    Fetch all clients with basic info.
    Returns list of tuples:
    (id, account_type, first_name, last_name, username, gender, mobile, email, password, status)
    Falls back if some columns missing.
    """
    cur = conn.cursor()
    # Try selecting with all columns
    try:
        cur.execute("""
            SELECT id, account_type, first_name, last_name,
                   username, gender, mobile, email, password, status
            FROM clients
        """)
        return cur.fetchall()
    except sqlite3.OperationalError:
        # Possibly missing username or gender; inspect existing cols and build SELECT accordingly
        cur.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in cur.fetchall()]
        select_cols = []
        # We want exactly the order: id, account_type, first_name, last_name, username, gender, mobile, email, password, status
        for col in ["id", "account_type", "first_name", "last_name", "username", "gender", "mobile", "email", "password", "status"]:
            if col in cols:
                select_cols.append(col)
            else:
                # supply NULL for optional columns
                if col in ("username", "gender", "mobile", "email", "password"):
                    select_cols.append(f"NULL AS {col}")
                else:
                    # core columns (id, account_type, first_name, last_name, status) assumed present
                    select_cols.append(col)
        query = "SELECT " + ", ".join(select_cols) + " FROM clients"
        cur.execute(query)
        return cur.fetchall()


def fetch_coaches_basic(conn: sqlite3.Connection):
    """
    Fetch all coaches (account_type='Coach') with basic info.
    Returns same tuple shape as fetch_all_clients_basic.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, account_type, first_name, last_name,
                   username, gender, mobile, email, password, status
            FROM clients
            WHERE account_type='Coach'
        """)
        return cur.fetchall()
    except sqlite3.OperationalError:
        # Fallback: inspect existing cols
        cur.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in cur.fetchall()]
        select_cols = []
        for col in ["id", "account_type", "first_name", "last_name", "username", "gender", "mobile", "email", "password", "status"]:
            if col in cols:
                select_cols.append(col)
            else:
                if col in ("username", "gender", "mobile", "email", "password"):
                    select_cols.append(f"NULL AS {col}")
                else:
                    select_cols.append(col)
        query = "SELECT " + ", ".join(select_cols) + " FROM clients WHERE account_type='Coach'"
        cur.execute(query)
        return cur.fetchall()


def fetch_athletes_basic(conn: sqlite3.Connection):
    """
    Fetch all athletes (account_type='Athlete') with basic info.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, account_type, first_name, last_name,
                   username, gender, mobile, email, password, status
            FROM clients
            WHERE account_type='Athlete'
        """)
        return cur.fetchall()
    except sqlite3.OperationalError:
        # Fallback: inspect existing cols
        cur.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in cur.fetchall()]
        select_cols = []
        for col in ["id", "account_type", "first_name", "last_name", "username", "gender", "mobile", "email", "password", "status"]:
            if col in cols:
                select_cols.append(col)
            else:
                if col in ("username", "gender", "mobile", "email", "password"):
                    select_cols.append(f"NULL AS {col}")
                else:
                    select_cols.append(col)
        query = "SELECT " + ", ".join(select_cols) + " FROM clients WHERE account_type='Athlete'"
        cur.execute(query)
        return cur.fetchall()


def fetch_all_groups(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Fetch all hierarchical groups as a DataFrame with columns:
    id, group_parent, club, group_name, group_sub.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT id, group_parent, club, group_name, group_sub
        FROM group_hierarchy
        ORDER BY group_parent, club, group_name, group_sub
    """)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["id", "group_parent", "club", "group_name", "group_sub"])
    return df


def insert_group_row(conn: sqlite3.Connection, group_parent: str, club: str, group_name: str, group_sub: str):
    """
    Insert one row into group_hierarchy.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO group_hierarchy(group_parent, club, group_name, group_sub)
        VALUES (?, ?, ?, ?)
    """, (
        group_parent if group_parent else None,
        club if club else None,
        group_name,
        group_sub if group_sub else None
    ))
    conn.commit()


def update_group_row(conn: sqlite3.Connection, gid: int, group_parent: str, club: str, group_name: str, group_sub: str):
    """
    Update an existing group_hierarchy row by id.
    """
    cur = conn.cursor()
    cur.execute("""
        UPDATE group_hierarchy
           SET group_parent=?, club=?, group_name=?, group_sub=?
         WHERE id=?
    """, (
        group_parent if group_parent else None,
        club if club else None,
        group_name,
        group_sub if group_sub else None,
        gid
    ))
    conn.commit()


def delete_group_row(conn: sqlite3.Connection, gid: int):
    """
    Delete a group_hierarchy row; cascades on user_group_assignments if foreign keys enabled.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM group_hierarchy WHERE id=?", (gid,))
    conn.commit()


def fetch_user_groups(conn: sqlite3.Connection, user_id: str) -> list[int]:
    """
    Given a user_id, return list of group_hierarchy.id that the user is assigned to.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT group_id FROM user_group_assignments WHERE user_id=?
        """, (user_id,))
        return [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError:
        # Table might not exist yet
        return []


def assign_user_to_groups(conn: sqlite3.Connection, user_id: str, group_ids: list[int]):
    """
    Assign a user to exactly the given list of group_ids.
    Clears previous assignments first.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM user_group_assignments WHERE user_id=?", (user_id,))
    for gid in group_ids:
        cur.execute("""
            INSERT OR IGNORE INTO user_group_assignments(user_id, group_id)
            VALUES (?, ?)
        """, (user_id, gid))
    conn.commit()


def fetch_groups_with_members(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Returns a DataFrame listing each group row plus comma-separated lists of assigned coaches and athletes.
    Columns: ['id','group_parent','club','group_name','group_sub','coaches','athletes']
    """
    cur = conn.cursor()
    # Use GROUP_CONCAT to gather names
    query = """
        SELECT
            gh.id,
            gh.group_parent,
            gh.club,
            gh.group_name,
            gh.group_sub,
            GROUP_CONCAT(CASE WHEN c.account_type='Coach' THEN c.first_name || ' ' || c.last_name END, ', ') AS coaches,
            GROUP_CONCAT(CASE WHEN c.account_type='Athlete' THEN c.first_name || ' ' || c.last_name END, ', ') AS athletes
        FROM group_hierarchy gh
        LEFT JOIN user_group_assignments uga ON gh.id = uga.group_id
        LEFT JOIN clients c ON uga.user_id = c.id
        GROUP BY gh.id, gh.group_parent, gh.club, gh.group_name, gh.group_sub
        ORDER BY gh.group_parent, gh.club, gh.group_name, gh.group_sub
    """
    try:
        cur.execute(query)
        rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=[
            "id", "group_parent", "club", "group_name", "group_sub", "coaches", "athletes"
        ])
        # Replace None/NULL in coaches/athletes with empty string
        df["coaches"] = df["coaches"].fillna("").astype(str)
        df["athletes"] = df["athletes"].fillna("").astype(str)
        return df
    except sqlite3.OperationalError:
        # If tables missing or columns missing, return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            "id", "group_parent", "club", "group_name", "group_sub", "coaches", "athletes"
        ])


def delete_client(conn: sqlite3.Connection, user_id: str):
    """
    Delete a client by ID. Cascades in user_group_assignments if foreign keys ON.
    Also may wish to delete related patient_status dir / PDFs externally in Settings page.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE id=?", (user_id,))
    conn.commit()


@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Loads and returns the exercise database CSV as a pandas DataFrame.
    Uses utf-8 encoding with fallback to ISO-8859-1.
    """
    if not EXERCISE_DB_PATH.exists():
        st.error(f"Exercise database CSV not found at: {EXERCISE_DB_PATH}")
        st.stop()
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
