import re
from src.database import connect

# Only non-sensitive, useful academic preferences/programme information is permitted.
BLOCKED_TERMS = {
    "password", "otp", "one time password", "credit card", "debit card",
    "bank account", "cvv", "medical", "diagnosis", "health condition",
    "religion", "political", "aadhaar", "pan number", "passport"
}
ALLOWED_HINTS = ("programme", "program", "course", "major", "elective", "preference", "prefer", "learning style", "communication")

def validate_memory(value):
    text = (value or "").strip()
    if not text:
        raise ValueError("Please enter a memory first.")
    low = text.lower()
    if any(term in low for term in BLOCKED_TERMS):
        raise ValueError("This looks like sensitive information. CampusCare will not save it.")
    if len(text) > 240:
        raise ValueError("Keep a memory under 240 characters.")
    if not any(h in low for h in ALLOWED_HINTS):
        raise ValueError("Only programme, course, elective or learning/communication preferences can be saved.")
    return text

def save_memory(student_id, value, category="academic_preference"):
    text = validate_memory(value)
    with connect() as con:
        con.execute(
            "INSERT INTO memories(student_id,category,memory_text,created_at) VALUES(?,?,?,datetime('now'))",
            (student_id, category, text)
        )
    return {"saved": True, "memory_text": text}

def get_memories(student_id):
    with connect() as con:
        rows = con.execute(
            "SELECT memory_id,category,memory_text,created_at FROM memories WHERE student_id=? ORDER BY memory_id DESC LIMIT 12",
            (student_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def relevant_memories(student_id, question, limit=3):
    memories = get_memories(student_id)
    q_words = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    scored = []
    for item in memories:
        words = set(re.findall(r"[a-zA-Z]{3,}", item["memory_text"].lower()))
        score = len(q_words & words)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:limit]]
