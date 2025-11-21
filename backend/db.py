# db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()  # Load .env file


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_HOST"),
        port="6543",
        database="postgres",
        user=os.getenv("SUPABASE_USER"),
        password=os.getenv("SUPABASE_PASSWORD")
    )

@contextmanager
def get_cursor():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield conn, cur
    finally:
        try:
            cur.close()
        except:
            pass
        conn.close()
