"""MySQL helpers (connection pool + tiny query wrappers)."""
import os
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()
CFG = dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
           user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""))
DB_NAME = os.getenv("DB_NAME", "staygenius")
_pool = None


def get_conn():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(pool_name="sg", pool_size=10, database=DB_NAME,
                                            autocommit=True, **CFG)
    return _pool.get_connection()


def query(sql, params=(), one=False):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        lid = cur.lastrowid
        cur.close()
        return lid
    finally:
        conn.close()
