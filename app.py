import os
import time
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from src.database import initialize_database, get_student_ids
from src.agent import run_agent
from src.memory import save_memory, get_memories
from src.evaluation import run_evaluation

load_dotenv()
st.set_page_config(page_title="CampusCare AI | Student Support", page_icon="🎓", layout="wide")

initialize_database()

st.markdown("""
<style>
.main {background: #f7f9fc;}
.block-container {padding-top: 1.8rem; max-width: 1180px;}
.hero {padding: 1.35rem 1.6rem; border-radius: 18px; background: linear-gradient(120deg,#14213d,#315c91); color:white; margin-bottom:1rem;}
.hero h1 {color:white; margin:0;}
.hero p {color:#e5edf8; margin:.35rem 0 0 0;}
[data-testid="stChatMessage"] {border-radius: 14px;}
.small-note {color:#667085; font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🎓 CampusCare AI</h1>
  <p>Your intelligent student support assistant · Fees · Scholarships · Policies · Support tickets</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Student profile")
    ids = get_student_ids()
    if not ids:
        st.error("No sample students found. Check the data folder.")
        st.stop()
    selected_id = st.selectbox("Choose a demo student", ids, index=0)
    st.caption("Use the sample IDs included in this project. This is fictional demo data.")
    st.divider()
    st.subheader("API configuration")
    api_key_present = bool(os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", ""))
    if api_key_present:
        st.success("Groq API key detected")
    else:
        st.warning("Groq API key not found")
        st.caption("Add GROQ_API_KEY to the .env file, then restart Streamlit.")
    model_name = st.text_input("Groq model", value=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    st.divider()
    st.subheader("Long-term memory")
    st.caption("Only non-sensitive programme details and preferences should be saved.")
    memory_text = st.text_input("Add a useful memory", placeholder="My programme is PGDM in Business Analytics")
    if st.button("Save memory", use_container_width=True):
        try:
            save_memory(selected_id, memory_text)
            st.success("Memory saved.")
        except ValueError as e:
            st.error(str(e))
    memories = get_memories(selected_id)
    if memories:
        with st.expander(f"Saved memories ({len(memories)})"):
            for item in memories:
                st.write(f"• {item['memory_text']}")
    st.divider()
    st.caption("CampusCare AI · Academic demonstration build")

tab_chat, tab_data, tab_eval, tab_about = st.tabs(["💬 Chat assistant", "🗂️ Sample data", "📊 Evaluation & traces", "ℹ️ How it works"])

with tab_chat:
    st.subheader("Ask your student support question")
    st.caption(f"Active demo student: **{selected_id}**. Ask about fees, scholarships, payment rules, course changes or support.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_student" not in st.session_state:
        st.session_state.chat_student = selected_id
    if st.session_state.chat_student != selected_id:
        st.session_state.messages = []
        st.session_state.chat_student = selected_id

    examples = [
        "What is my current fee status?",
        "What scholarship am I eligible for?",
        "The payment portal failed. Can I pay on the next working day?",
        "I want to change my elective. What is the process?",
        "Please create a support ticket because my student portal is not working."
    ]
    with st.expander("Try a sample question"):
        cols = st.columns(2)
        for i, q in enumerate(examples):
            if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
                st.session_state.pending_question = q

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("trace"):
                with st.expander("View agent trace"):
                    st.json(msg["trace"])

    prompt = st.chat_input("Type your question here…")
    if "pending_question" in st.session_state:
        prompt = st.session_state.pop("pending_question")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            if not api_key_present:
                answer = ("I can't contact the AI model because the Groq API key is missing. "
                          "Create a key at https://console.groq.com/keys and add it to the project's `.env` file.")
                st.error(answer)
                result = {"answer": answer, "trace": {"error": "Missing GROQ_API_KEY"}, "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
            else:
                with st.spinner("CampusCare is checking the relevant records and policies…"):
                    try:
                        result = run_agent(
                            question=prompt,
                            student_id=selected_id,
                            model=model_name,
                            conversation=st.session_state.messages[-7:-1]
                        )
                        answer = result["answer"]
                        st.markdown(answer)
                        with st.expander("View agent trace"):
                            st.json(result["trace"])
                    except Exception as exc:
                        answer = f"Something went wrong while contacting Groq: {exc}"
                        result = {"answer": answer, "trace": {"error": str(exc)}, "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
                        st.error(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer, "trace": result.get("trace")})
        st.rerun()

with tab_data:
    st.subheader("Included fictional sample records")
    st.info("These are invented records for testing. Replace them with authorized institutional data only if you have permission.")
    from src.database import get_all_students, get_fee_records, get_scholarship_records, get_tickets
    st.markdown("**Students**")
    st.dataframe(pd.DataFrame(get_all_students()), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Fee records**")
        st.dataframe(pd.DataFrame(get_fee_records()), use_container_width=True, hide_index=True)
    with c2:
        st.markdown("**Scholarship records**")
        st.dataframe(pd.DataFrame(get_scholarship_records()), use_container_width=True, hide_index=True)
    st.markdown("**Support tickets created during this run**")
    st.dataframe(pd.DataFrame(get_tickets()), use_container_width=True, hide_index=True)

with tab_eval:
    st.subheader("Assignment evaluation")
    st.write("Runs a fixed set of demo questions through the same agent loop and records success, tools, latency, token usage and evidence.")
    st.warning("Evaluation calls Groq and may consume API quota.")
    if st.button("Run evaluation suite", type="primary"):
        if not api_key_present:
            st.error("Add your Groq API key first.")
        else:
            with st.spinner("Running test questions…"):
                report = run_evaluation(selected_id, model_name)
                st.session_state.eval_report = report
    if "eval_report" in st.session_state:
        report = st.session_state.eval_report
        df = pd.DataFrame(report["rows"])
        a, b, c = st.columns(3)
        a.metric("Successful tests", f"{report['success_count']}/{len(df)}")
        b.metric("Success rate", f"{report['accuracy']:.0%}")
        c.metric("Average latency", f"{report['average_latency']:.2f}s")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download evaluation CSV", df.to_csv(index=False).encode("utf-8"), "evaluation_results.csv", "text/csv")
        st.caption("Token counts are reported by Groq when supplied by the API. Success is checked using expected tool/evidence markers and should be reviewed manually before submission.")

with tab_about:
    st.subheader("Project architecture")
    st.markdown("""
1. **Streamlit UI** receives the student's question and selected demo student ID.
2. **Agent loop** sends the question, limited conversation history and relevant saved memory to Groq.
3. **Tool selection**: Groq can choose fee lookup, scholarship lookup, policy search, student record lookup or ticket creation.
4. **Policy retrieval** uses TF-IDF to select only the most relevant handbook sections.
5. **SQLite** stores sample student records, support tickets and long-term non-sensitive memory.
6. **Observability** records tool names, retrieved evidence, approximate latency and API token usage.

### Privacy and safety choices
- The demo uses fictional student records.
- Long-term memory is restricted to non-sensitive programme and preference information.
- Passwords, financial credentials, health information and other sensitive details must not be saved as memory.
- The app does not make real payments or change official academic records.
""")
    st.markdown("**Main files:** `app.py`, `src/agent.py`, `src/tools.py`, `src/retrieval.py`, `src/database.py`, `src/memory.py`, `data/`, and `knowledge_base/student_handbook.md`.")
