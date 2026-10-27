import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nlp.db")
DEFAULT_SETTINGS = {"mode": "accurate", "length": "medium", "theme": "light"}


def _run(sql, args=(), fetch=None):
    """Open the database, run one statement, save, close. fetch = 'one', 'all' or None."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, args)
        rows = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else None
        conn.commit()
        return rows
    finally:
        conn.close()


def init_db():
    _run("""CREATE TABLE IF NOT EXISTS papers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, filename TEXT, mode TEXT,
        length TEXT, created TEXT, result_json TEXT)""")
    _run("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, event TEXT, detail TEXT, outcome TEXT, ms INTEGER)""")
    _run("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---- papers ----
def add_paper(filename, mode, length, result):
    """Save a result. The id is only known after saving, so the title is finished afterwards."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "INSERT INTO papers(title, filename, mode, length, created, result_json) VALUES('', ?, ?, ?, ?, '')",
            (filename, mode, length, _now()))
        pid = cur.lastrowid
        result["paper_id"] = pid
        result["title"] = f"Paper {pid}: {result['title']}"
        conn.execute("UPDATE papers SET title=?, result_json=? WHERE id=?", (result["title"], json.dumps(result), pid))
        conn.commit()
    finally:
        conn.close()
    return result


def list_papers():
    rows = _run("SELECT id, title, filename, mode, length, created FROM papers ORDER BY id DESC", fetch="all")
    return [dict(r) for r in rows]


def get_paper(pid):
    row = _run("SELECT result_json FROM papers WHERE id=?", (pid,), fetch="one")
    return json.loads(row["result_json"]) if row else None


def delete_paper(pid):
    _run("DELETE FROM papers WHERE id=?", (pid,))


# ---- history (audit log) ----
def log_event(event, detail="", outcome="ok", ms=0):
    _run("INSERT INTO history(time, event, detail, outcome, ms) VALUES(?, ?, ?, ?, ?)",
         (_now(), event, detail, outcome, ms))


def list_history(limit=500):
    rows = _run("SELECT time, event, detail, outcome, ms FROM history ORDER BY id DESC LIMIT ?", (limit,), fetch="all")
    return [dict(r) for r in rows]


def clear_history():
    _run("DELETE FROM history")


# ---- settings ----
def get_settings():
    rows = _run("SELECT key, value FROM settings", fetch="all")
    return {**DEFAULT_SETTINGS, **{r["key"]: r["value"] for r in rows}}


def save_settings(new):
    for key in DEFAULT_SETTINGS:
        if key in new:
            _run("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, str(new[key])))
    return get_settings()