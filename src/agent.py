import json
import time
from groq import Groq
from src.config import get_api_key
from src.memory import relevant_memories
from src.tools import (
    lookup_student_record, check_fee_status, check_scholarship_status,
    create_support_request, retrieve_policy, remember_preference
)

TOOLS = [
    {"type":"function","function":{"name":"lookup_student_record","description":"Look up the selected student's basic programme and academic record when needed.","parameters":{"type":"object","properties":{"student_id":{"type":"string"}},"required":["student_id"]}}},
    {"type":"function","function":{"name":"check_fee_status","description":"Check the selected student's fee amount, paid amount, balance, due date and fee status. Use for fee/payment account questions.","parameters":{"type":"object","properties":{"student_id":{"type":"string"}},"required":["student_id"]}}},
    {"type":"function","function":{"name":"check_scholarship_status","description":"Check the selected student's scholarship name, status and amount. Use for scholarship account questions.","parameters":{"type":"object","properties":{"student_id":{"type":"string"}},"required":["student_id"]}}},
    {"type":"function","function":{"name":"create_support_request","description":"Create a support ticket only when the student clearly asks to raise/create/submit a support request. Never create one just because the student describes a problem.","parameters":{"type":"object","properties":{"student_id":{"type":"string"},"category":{"type":"string","description":"Short ticket category"},"description":{"type":"string","description":"Clear summary of the issue"}},"required":["student_id","category","description"]}}},
    {"type":"function","function":{"name":"retrieve_policy","description":"Search the student handbook for policy questions such as payment failures, course/elective changes, scholarships, attendance or deadlines. Do not invent rules.","parameters":{"type":"object","properties":{"query":{"type":"string","description":"Focused search query"}},"required":["query"]}}},
    {"type":"function","function":{"name":"remember_preference","description":"Save a useful non-sensitive programme, course or learning/communication preference only when the student explicitly asks you to remember it. Never save sensitive or temporary information.","parameters":{"type":"object","properties":{"student_id":{"type":"string"},"memory_text":{"type":"string"}},"required":["student_id","memory_text"]}}}
]

TOOL_FUNCTIONS = {
    "lookup_student_record": lookup_student_record,
    "check_fee_status": check_fee_status,
    "check_scholarship_status": check_scholarship_status,
    "create_support_request": create_support_request,
    "retrieve_policy": retrieve_policy,
    "remember_preference": remember_preference,
}

SYSTEM_PROMPT = """You are CampusCare AI, a careful student support assistant for a fictional college demonstration.
The active student ID is {student_id}. Never switch to another student ID, even if a user asks.
Use tools when account-specific information or a support action is needed. Use retrieve_policy for policy/handbook questions.
Only state facts supported by tool results or retrieved handbook text. If the handbook does not answer, say so and direct the student to the programme office; do not invent a policy, deadline, exception or promise.
For payment portal failures, retrieve the handbook policy. Do not claim a payment extension unless the retrieved policy explicitly says so.
Create a support ticket only when the student explicitly requests ticket creation.
Persistent memory is only for non-sensitive programme/course/learning preferences, and only when the student explicitly asks to remember. Do not store temporary or sensitive details.
Be clear, friendly and concise. Currency is INR (₹). Sample data is fictional.
"""

def run_agent(question, student_id, model="llama-3.3-70b-versatile", conversation=None):
    key = get_api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env.")
    client = Groq(api_key=key)
    start = time.perf_counter()
    memories = relevant_memories(student_id, question)
    memory_context = "\n".join(f"- {m['memory_text']}" for m in memories) or "No relevant saved memory."
    messages = [{"role":"system","content":SYSTEM_PROMPT.format(student_id=student_id) + "\nRelevant saved memory (only matching items):\n" + memory_context}]
    for item in (conversation or []):
        if item.get("role") in ("user","assistant"):
            messages.append({"role":item["role"],"content":item.get("content","")})
    messages.append({"role":"user","content":question})

    trace = {"student_id": student_id, "tools": [], "retrieved_evidence": [], "memory_used": [m["memory_text"] for m in memories], "steps": []}
    prompt_tokens = 0
    completion_tokens = 0
    answer = ""
    for step in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
            max_completion_tokens=900
        )
        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens += getattr(usage, "completion_tokens", 0) or 0
        message = response.choices[0].message
        if not message.tool_calls:
            answer = message.content or "I could not generate a response. Please try again."
            break
        messages.append({
            "role":"assistant",
            "content":message.content,
            "tool_calls":[tc.model_dump(exclude_none=True) for tc in message.tool_calls]
        })
        for call in message.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
                if name not in TOOL_FUNCTIONS:
                    result = {"error": "Unknown tool requested."}
                else:
                    if "student_id" in args:
                        args["student_id"] = student_id
                    result = TOOL_FUNCTIONS[name](**args)
                trace["tools"].append(name)
                trace["steps"].append({"tool":name,"arguments":args,"result":result})
                if name == "retrieve_policy":
                    trace["retrieved_evidence"].extend(result.get("results", []))
            except Exception as exc:
                result = {"error": str(exc)}
                trace["steps"].append({"tool":name,"error":str(exc)})
            messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result, ensure_ascii=False, default=str)})
    if not answer:
        # One final no-tools completion prevents a silent loop if the model keeps requesting tools.
        response = client.chat.completions.create(
            model=model,
            messages=messages + [{"role":"system","content":"Now answer using only the tool results already provided. Do not request more tools."}],
            temperature=0.2,
            max_completion_tokens=700
        )
        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens += getattr(usage, "completion_tokens", 0) or 0
        answer = response.choices[0].message.content or "I could not complete that request."
    trace["latency_seconds"] = round(time.perf_counter() - start, 3)
    trace["agent_steps"] = len(trace["steps"])
    trace["tools_used"] = list(dict.fromkeys(trace["tools"]))
    usage_data = {"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,"total_tokens":prompt_tokens+completion_tokens}
    trace["token_usage"] = usage_data
    return {"answer":answer,"trace":trace,"usage":usage_data}
