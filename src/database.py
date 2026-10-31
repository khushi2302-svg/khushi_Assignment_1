import sqlite3
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "campuscare.db"

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _read_csv(filename):
    with open(ROOT / "data" / filename, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def initialize_database():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY, full_name TEXT, programme TEXT,
            year TEXT, email TEXT, department TEXT
        );
        CREATE TABLE IF NOT EXISTS fees (
            student_id TEXT PRIMARY KEY, total_fee REAL, paid_amount REAL,
            due_date TEXT, status TEXT, FOREIGN KEY(student_id) REFERENCES students(student_id)
        );
        CREATE TABLE IF NOT EXISTS scholarships (
            student_id TEXT PRIMARY KEY, scholarship_name TEXT, status TEXT,
            amount REAL, remarks TEXT, FOREIGN KEY(student_id) REFERENCES students(student_id)
        );
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
            category TEXT, description TEXT, status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS memories (
            memory_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
            category TEXT, memory_text TEXT, created_at TEXT
        );
        """)
        if con.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            for row in _read_csv("students.csv"):
                con.execute("INSERT INTO students VALUES (?,?,?,?,?,?)", tuple(row[k] for k in ["student_id","full_name","programme","year","email","department"]))
            for row in _read_csv("fees.csv"):
                con.execute("INSERT INTO fees VALUES (?,?,?,?,?)", tuple(row[k] for k in ["student_id","total_fee","paid_amount","due_date","status"]))
            for row in _read_csv("scholarships.csv"):
                con.execute("INSERT INTO scholarships VALUES (?,?,?,?,?)", tuple(row[k] for k in ["student_id","scholarship_name","status","amount","remarks"]))

def get_student_ids():
    with connect() as con:
        return [r["student_id"] for r in con.execute("SELECT student_id FROM students ORDER BY student_id")]

def get_student(student_id):
    with connect() as con:
        r = con.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
        return dict(r) if r else None

def get_fee(student_id):
    with connect() as con:
        r = con.execute("SELECT * FROM fees WHERE student_id=?", (student_id,)).fetchone()
        return dict(r) if r else None

def get_scholarship(student_id):
    with connect() as con:
        r = con.execute("SELECT * FROM scholarships WHERE student_id=?", (student_id,)).fetchone()
        return dict(r) if r else None

def create_ticket(student_id, category, description):
    from datetime import datetime, timezone
    with connect() as con:
        cur = con.execute(
            "INSERT INTO tickets(student_id,category,description,status,created_at) VALUES(?,?,?,?,?)",
            (student_id, category[:60], description[:500], "Open", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        )
        return {"ticket_id": cur.lastrowid, "student_id": student_id, "category": category, "status": "Open"}

def get_all_students():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM students")]

def get_fee_records():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM fees")]

def get_scholarship_records():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM scholarships")]

def get_tickets():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM tickets ORDER BY ticket_id DESC")]
