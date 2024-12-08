import sqlite3

from src.constants import DB_FILE, SCRIPT_DIR
import os


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)
        raise e
    return conn

def init():
    conn = create_connection(DB_FILE)
    c = conn.cursor()
    # open file in db/sql/table.sql
    sqlfile = os.path.join(SCRIPT_DIR, 'db', 'sql', 'table_setup.sql')
    with open(sqlfile, 'r') as f:
        sql = f.read()
        c.executescript(sql)
    conn.commit()
    return conn

def set_config(conn: sqlite3.Connection, key, value):
    c = conn.cursor()
    print(f"Setting config {key} to {value}")
    c.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    return value


def get_config(conn: sqlite3.Connection, key, default=None):
    c = conn.cursor()
    c.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = c.fetchone()
    if row:
        return row[0]
    if default:
        set_config(conn, key, default)
    return default

def get_float_config(conn: sqlite3.Connection, key, default=0.0):
    value = get_config(conn, key, default)
    return float(value)