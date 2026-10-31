from src.database import get_student, get_fee, get_scholarship, create_ticket
from src.retrieval import search_policy
from src.memory import save_memory

def lookup_student_record(student_id):
    row = get_student(student_id)
    if not row:
        return {"found": False, "message": f"No student record found for {student_id}."}
    # Do not expose the student's email address unless specifically needed.
    row.pop("email", None)
    return {"found": True, "student": row}

def check_fee_status(student_id):
    row = get_fee(student_id)
    if not row:
        return {"found": False, "message": "Fee record not found."}
    row["balance"] = round(float(row["total_fee"]) - float(row["paid_amount"]), 2)
    return {"found": True, "fee_record": row}

def check_scholarship_status(student_id):
    row = get_scholarship(student_id)
    if not row:
        return {"found": False, "message": "Scholarship record not found."}
    return {"found": True, "scholarship": row}

def create_support_request(student_id, category, description):
    if len(description.strip()) < 8:
        return {"created": False, "message": "Please provide a little more detail before creating a ticket."}
    return {"created": True, "ticket": create_ticket(student_id, category, description)}

def retrieve_policy(query):
    results = search_policy(query, top_k=2)
    return {"results": results, "message": "No relevant handbook section was found." if not results else "Relevant handbook sections retrieved."}

def remember_preference(student_id, memory_text):
    try:
        return save_memory(student_id, memory_text)
    except ValueError as exc:
        return {"saved": False, "message": str(exc)}
