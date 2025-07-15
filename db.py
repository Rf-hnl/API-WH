# db.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes a database connection and returns the connection object."""
    conn = psycopg2.connect(os.getenv('DIRECT_URL'))
    return conn

def query_db(query, args=(), one=False):
    """Queries the database and returns the results."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query, args)
    results = cur.fetchone() if one else cur.fetchall()
    cur.close()
    conn.close()
    return results
