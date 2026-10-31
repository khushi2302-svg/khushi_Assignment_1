from src.agent import run_agent

TESTS = [
    {"question":"What is my current fee status?","expected_tool":"check_fee_status","name":"Fee status lookup"},
    {"question":"What scholarship am I receiving?","expected_tool":"check_scholarship_status","name":"Scholarship lookup"},
    {"question":"The payment portal failed. Can I pay on the next working day?","expected_tool":"retrieve_policy","name":"Payment failure policy"},
    {"question":"What is the process to change my elective?","expected_tool":"retrieve_policy","name":"Elective change policy"},
    {"question":"Please create a support ticket because my student portal is not working.","expected_tool":"create_support_request","name":"Create support ticket"}
]

def run_evaluation(student_id, model):
    rows = []
    for test in TESTS:
        try:
            result = run_agent(test["question"], student_id, model=model)
            tools = result["trace"].get("tools_used", [])
            expected = test["expected_tool"]
            success = expected in tools
            rows.append({
                "test":test["name"],
                "question":test["question"],
                "expected_tool":expected,
                "tools_used":", ".join(tools) or "None",
                "success":success,
                "latency_seconds":result["trace"].get("latency_seconds",0),
                "input_tokens":result["usage"]["prompt_tokens"],
                "output_tokens":result["usage"]["completion_tokens"],
                "retrieved_evidence":", ".join(x["chunk_id"] for x in result["trace"].get("retrieved_evidence",[])),
                "observation":result["answer"][:220].replace("\\n"," ")
            })
        except Exception as exc:
            rows.append({"test":test["name"],"question":test["question"],"expected_tool":test["expected_tool"],"tools_used":"Error","success":False,"latency_seconds":0,"input_tokens":0,"output_tokens":0,"retrieved_evidence":"","observation":str(exc)[:220]})
    successes = sum(1 for r in rows if r["success"])
    return {"rows":rows,"success_count":successes,"accuracy":successes/len(rows) if rows else 0,"average_latency":sum(r["latency_seconds"] for r in rows)/len(rows) if rows else 0}
