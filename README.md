# CampusCare AI — Intelligent Student Support Agent (Assignment 1)

## 1. Project overview

CampusCare AI is a Streamlit-based student support assistant that uses a Groq-hosted language model, Python tools and a local SQLite database to answer common student questions. It can retrieve student, fee and scholarship information, search a sample student handbook, create support tickets and save selected non-sensitive academic preferences as long-term memory.

The application is designed as an academic demonstration. The included student, fee and scholarship records are fictional sample data and should not be treated as official institutional records or policies.

## 2. Objectives and capabilities

The supplied implementation demonstrates these Agentic AI Engineering concepts:

- **LLM agent loop:** the model can choose from a set of tools, receive the tool results and then formulate an answer.
- **Tool integration:** student record lookup, fee status, scholarship status, support ticket creation, handbook retrieval and memory saving.
- **Persistent memory:** selected academic preferences are stored in SQLite and can be reused in later sessions.
- **Relevant memory selection:** only saved memories that share words with the current question are added to the agent context.
- **Policy retrieval:** TF-IDF and cosine similarity rank sections from a Markdown student handbook.
- **Context management:** the agent receives the selected student ID, up to three relevant memories and a limited recent conversation history.
- **Execution traces:** tool calls, arguments, results, retrieved evidence, latency and token usage are collected for inspection.
- **Evaluation:** a five-question test suite checks whether the expected tool was called and reports success rate and average latency.

## 3. Technology stack

| Technology | Use in the project |
|---|---|
| Python | Application, agent and tool logic |
| Streamlit | Chat interface, student selector, memory controls, sample-data view and evaluation dashboard |
| Groq Python SDK | Chat completion requests and function/tool calling |
| SQLite | Student, fee, scholarship, ticket and memory storage |
| pandas | Displaying tables and exporting evaluation results to CSV |
| scikit-learn | TF-IDF vectorization and cosine-similarity ranking |
| python-dotenv | Loading environment variables from `.env` |

The exact pinned dependency versions should be taken from the project's `requirements.txt`. That file was not included in the files supplied for this README, so package versions are not listed here.

## 4. Project structure

```text
CampusCare_AI/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── data/
│   ├── students.csv
│   ├── fees.csv
│   ├── scholarships.csv
│   └── campuscare.db             # generated at runtime
│
├── evaluation/
│   ├── assignment_checklist.md
│   └── test_scenarios.csv
│
├── knowledge_base/
│   └── student_handbook.md
│
└── src/
    ├── __init__.py
    ├── agent.py
    ├── config.py
    ├── database.py
    ├── evaluation.py
    ├── memory.py
    ├── retrieval.py
    └── tools.py
```

`data/campuscare.db` is created by the application. The handbook file is required by the retrieval module and must be present at `knowledge_base/student_handbook.md`. The handbook itself was not included in the uploaded materials, so this README documents the retrieval implementation but does not describe the handbook's specific policy content.

## 5. Application workflow

1. **Initialize the database:** `initialize_database()` creates the SQLite tables. If the `students` table is empty, it imports the student, fee and scholarship CSV data.
2. **Select a demo student:** the sidebar loads the available student IDs from the database and lets the user choose one.
3. **Submit a question:** the student asks a question in the Streamlit chat interface or selects one of the sample prompts.
4. **Select relevant memory:** `run_agent()` calls `relevant_memories()` to find up to three saved memories that share words with the current question.
5. **Prepare model context:** the agent builds a system prompt containing the selected student ID and relevant memories, adds the recent conversation messages supplied by the UI, and appends the current question.
6. **Choose a tool:** Groq receives the available function definitions and may respond with a tool call or a direct answer.
7. **Execute the tool:** the agent maps the requested function to a Python function in `src/tools.py`. Student IDs in tool arguments are overwritten with the currently selected student ID before the tool is called.
8. **Return tool results:** tool outputs are added to the conversation as tool messages so the model can use them in its next response.
9. **Produce the final answer:** the agent returns the answer and a trace containing tool usage, steps, evidence, latency and token counts.
10. **Inspect and evaluate:** the UI displays sample data, evaluation results and traces.

The agent permits up to five tool-call iterations. If it still has not produced an answer, it makes one final model request instructing the model to answer using the tool results already available.

## 6. Agent tools

The agent defines six tools in `src/agent.py`.

| Tool | Purpose | Implementation |
|---|---|---|
| `lookup_student_record` | Retrieves the selected student's basic programme and academic record. The email field is removed from the returned result. | `lookup_student_record()` in `src/tools.py` |
| `check_fee_status` | Retrieves fee amount, amount paid, due date and status; calculates the outstanding balance. | `check_fee_status()` in `src/tools.py` |
| `check_scholarship_status` | Retrieves scholarship name, status, amount and remarks. | `check_scholarship_status()` in `src/tools.py` |
| `create_support_request` | Creates an `Open` support ticket after the student explicitly asks for one and provides a sufficiently detailed issue. | `create_support_request()` in `src/tools.py` |
| `retrieve_policy` | Searches the student handbook and returns up to two relevant sections. | `retrieve_policy()` in `src/tools.py`; `search_policy()` in `src/retrieval.py` |
| `remember_preference` | Saves a permitted non-sensitive academic or learning preference when explicitly requested. | `remember_preference()` in `src/tools.py`; `save_memory()` in `src/memory.py` |

### Tool execution behavior

- The model receives tool names, descriptions and argument schemas.
- `run_agent()` checks whether the requested tool exists in `TOOL_FUNCTIONS`.
- If the arguments include `student_id`, the agent replaces that value with the currently selected student ID before executing the tool.
- Tool results are added to the conversation and made available to the model.
- Each successful tool execution is added to the trace with its arguments and result.
- Exceptions raised during an individual tool call are converted into an error result and returned to the model.

The system prompt instructs the agent to create a support ticket only when the student clearly asks to create one. Merely describing a problem should not automatically create a ticket.

## 7. Student data and database design

The application stores its SQLite database at `data/campuscare.db`. `src/database.py` creates five tables.

| Table | Purpose | Main fields |
|---|---|---|
| `students` | Student profile and programme details. | `student_id`, `full_name`, `programme`, `year`, `email`, `department` |
| `fees` | Fee account details. | `student_id`, `total_fee`, `paid_amount`, `due_date`, `status` |
| `scholarships` | Scholarship application and award details. | `student_id`, `scholarship_name`, `status`, `amount`, `remarks` |
| `tickets` | Support requests created through the agent. | `ticket_id`, `student_id`, `category`, `description`, `status`, `created_at` |
| `memories` | Long-term student preference memories. | `memory_id`, `student_id`, `category`, `memory_text`, `created_at` |

### CSV seed data

When the students table is empty, `initialize_database()` loads:

- `data/students.csv` into the `students` table.
- `data/fees.csv` into the `fees` table.
- `data/scholarships.csv` into the `scholarships` table.

The uploaded sample CSVs contain five fictional student IDs: `STU1001` through `STU1005`.

### Fee balance calculation

The fee tool calculates the balance as:

`Balance = Total fee − Paid amount`

The result is rounded to two decimal places.

### Support ticket creation

The database function creates a ticket with status `Open` and a UTC timestamp. The category is limited to 60 characters and the description to 500 characters. The tool requires a description of at least eight non-whitespace characters before creating the ticket.

## 8. Policy retrieval (TF-IDF)

The retrieval module is `src/retrieval.py`. It reads the handbook at `knowledge_base/student_handbook.md`.

The retrieval process is:

1. Read the Markdown handbook.
2. Split its content into sections when a line begins with a Markdown heading (`#`).
3. Build a text chunk for each section, retaining its heading.
4. Combine each heading and section body for retrieval.
5. Use `TfidfVectorizer` with English stop words and unigram/bigram features (`ngram_range=(1, 2)`).
6. Calculate cosine similarity between the user's query and each handbook section.
7. Sort the sections by similarity and return up to the top two sections with a score greater than zero.

The returned result includes the chunk ID, heading, text and similarity score. These retrieved results are added to the agent trace as evidence.

The system prompt instructs the model not to invent policy details. If the handbook does not answer a question, the agent should say so and direct the student to the programme office. For payment portal failures, it must not promise an extension unless the retrieved policy explicitly supports it.

**Retrieval method:** the implementation uses TF-IDF and cosine similarity. It does not use a neural embedding model or vector database.

## 9. Persistent memory

Memory is implemented in `src/memory.py` and stored in the SQLite `memories` table.

### What can be saved

The memory validator allows useful academic information related to:
- Programme or course.
- Major or elective.
- Learning preferences.
- Communication preferences.

The memory text must be non-empty and no longer than 240 characters. It must contain one of the configured academic/preference hints.

### What is blocked

The validator blocks configured terms related to passwords, OTPs, bank/card details, medical or health information, diagnosis, religion, political information, Aadhaar, PAN and passport details.

### How memory is retrieved

- `get_memories()` loads up to the 12 most recent memories for the selected student.
- `relevant_memories()` compares words in the current question with words in each saved memory.
- Memories with at least one matching word are ranked by the number of shared words.
- The top three matching memories are included in the agent's system context.

This is a lightweight word-overlap relevance method, not semantic embedding search. The memory guard is keyword-based and cannot guarantee detection of every sensitive value.

The Streamlit sidebar also provides a manual memory input and a button to save a memory for the currently selected demo student.

## 10. Evaluation and execution traces

The evaluation logic is in `src/evaluation.py`. It defines five test questions:

| Test | Question / scenario | Expected tool |
|---|---|---|
| Fee status | What is my current fee status? | `check_fee_status` |
| Scholarship status | What scholarship am I receiving? | `check_scholarship_status` |
| Payment portal failure | The payment portal failed. Can I pay on the next working day? | `retrieve_policy` |
| Elective change | What is the process to change my elective? | `retrieve_policy` |
| Support request | Please create a support ticket because my student portal is not working. | `create_support_request` |

For each test, `run_evaluation()` runs the same agent workflow and checks whether the expected tool appears in the trace. It records:
- Test name and question.
- Expected tool and tools actually used.
- Success/failure of the expected-tool check.
- Latency in seconds.
- Input and output token counts.
- Retrieved evidence chunk IDs.
- A shortened observation from the agent answer.

The report calculates:

`Success rate = Successful tests / Total tests`

It also calculates average latency across the five tests. The UI displays the successful test count, success rate and average latency, and provides a CSV download.

**Evaluation limitation:** the automatic success check verifies expected tool selection, not full factual correctness or answer quality. The app itself warns that results should be reviewed manually before submission.

### Execution trace contents

The trace returned by `run_agent()` includes:
- Selected student ID.
- Tool names called.
- Each tool's arguments and result.
- Retrieved policy evidence.
- Relevant memories used.
- Number of agent tool steps.
- Total latency.
- Input, output and total token usage.

The chat interface displays an individual run trace. The evaluation tab displays the evaluation report and allows it to be downloaded.

## 11. Streamlit interface

The app contains four main tabs.

### Chat assistant
- Select a fictional demo student from the sidebar.
- Ask about fees, scholarships, payment rules, electives and support.
- Use sample prompts for common test questions.
- Inspect the agent trace for each answer.

### Sample data
- View student records.
- View fee records.
- View scholarship records.
- View support tickets created during the current database run.

### Evaluation & traces
- Run the five-question evaluation suite.
- View successful test count and success rate.
- View average latency and individual test results.
- Download the evaluation results as a CSV file.

Running the evaluation suite makes Groq API calls and may consume API quota.

### How it works
- Displays a short description of the application architecture.
- Summarizes privacy and safety choices described by the application.

## 12. Configuration and setup

### Prerequisites

- Windows 10/11 or another Python-compatible operating system.
- Python 3.10 or later (the existing project README recommends Python 3.11).
- Internet access for Groq API calls.
- A Groq API key and a model ID available to the account.

### Step 1 — Open the project folder

Open PowerShell or the VS Code terminal in the folder containing `app.py`.

### Step 2 — Create a virtual environment

```powershell
py -m venv .venv
```

### Step 3 — Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The exact `requirements.txt` was not included in the uploaded materials. Use the actual file from the project when installing dependencies.

### Step 4 — Configure environment variables

Copy `.env.example` to a new file named `.env`. Set the variables in this format:

```env
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=your_available_groq_model_id
```

`GROQ_API_KEY` must contain the API key. `GROQ_MODEL` must contain a model ID, not an API key. The UI initially uses the value of `GROQ_MODEL` and otherwise defaults to `llama-3.3-70b-versatile`; the selected model can also be changed in the sidebar.

Do not commit `.env` or share screenshots containing the API key.

### Step 5 — Run the application

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local Streamlit URL printed in the terminal, usually `http://localhost:8501`.

### Step 6 — Try the demo

Select one of the sample student IDs (`STU1001` to `STU1005`) and try:

- `What is my current fee status?`
- `What scholarship am I receiving?`
- `The payment portal failed. Can I pay on the next working day?`
- `What is the process to change my elective?`
- `Please create a support ticket because my student portal is not working.`

To demonstrate memory, enter a non-sensitive programme or learning preference in the sidebar, save it, and ask a related question. Restarting the app should retain the memory because it is stored in SQLite.

### Step 7 — Run evaluation

Open **Evaluation & traces**, click **Run evaluation suite**, review the five results and download the evaluation CSV.

## 13. File-by-file explanation

- **`app.py`** — Streamlit user interface, student selector, model selection, API-key status, manual memory saving, chat flow, sample-data display and evaluation dashboard.
- **`src/agent.py`** — tool definitions, system prompt, relevant-memory context, Groq tool-calling loop, tool execution, final response and trace creation.
- **`src/config.py`** — reads the Groq API key from environment variables or Streamlit secrets.
- **`src/database.py`** — creates SQLite tables, imports CSV data, retrieves students/fees/scholarships, creates tickets and exposes data for the UI.
- **`src/evaluation.py`** — defines the five evaluation questions, checks expected tool usage and calculates success rate and average latency.
- **`src/memory.py`** — validates memory text, blocks configured sensitive terms, saves memory, retrieves stored memory and ranks relevant memories by word overlap.
- **`src/retrieval.py`** — loads and chunks the handbook, creates TF-IDF vectors and ranks sections using cosine similarity.
- **`src/tools.py`** — implements the six callable tools by connecting agent requests to database, retrieval and memory functions.
- **`data/students.csv`** — fictional student profiles.
- **`data/fees.csv`** — fictional fee amounts, payments, due dates and statuses.
- **`data/scholarships.csv`** — fictional scholarship names, statuses, amounts and remarks.
- **`knowledge_base/student_handbook.md`** — source document for policy retrieval. This file was not included in the supplied upload and must be retained in the actual project.
- **`evaluation/test_scenarios.csv`** — five test questions, expected tool names and expected behavior.
- **`evaluation/assignment_checklist.md`** — manual demonstration checklist.
- **`requirements.txt`** — Python dependencies.
- **`.env.example`** — template for local Groq configuration; use placeholders only.
- **`data/campuscare.db`** — runtime SQLite database created by the app.

## 14. Scope and limitations

The supplied implementation is an academic demonstration. Its current limitations include:

1. **Demo student selector, not verified authentication:** a user selects a student ID in the sidebar. There is no password-based identity verification.
2. **No complete student authorization boundary:** the agent overwrites tool-supplied student IDs with the currently selected ID, which helps keep tool lookups tied to the selected profile. However, the UI exposes sample student, fee and scholarship tables, and the selector itself is not authentication. This is not a production privacy/security model.
3. **Local SQLite database:** no institutional database integration, encryption-at-rest configuration, backup strategy or multi-user deployment controls are included.
4. **Keyword-based memory filtering:** the blocked-term list is a basic guard and cannot detect every sensitive value or indirect phrasing.
5. **Simple memory relevance:** memory selection uses shared words rather than semantic embeddings.
6. **TF-IDF retrieval:** policy retrieval depends on wording overlap and the content/structure of the supplied handbook. It can miss relevant content expressed with different terms.
7. **Tool-selection evaluation:** the automatic evaluation checks expected tool usage, not whether every answer is factually correct. Manual review is required.
8. **Fictional data and handbook:** the sample data and policy document are for demonstration only.

The project does not make real payments, approve scholarships or modify official academic records.

## 15. GitHub submission checklist

Before publishing the repository:

- Include the Python source files, `requirements.txt`, README, `.env.example`, `.gitignore`, sample CSV files, handbook and evaluation files.
- Keep `.env.example` limited to placeholder values. It must not contain a real API key.
- Do not upload `.env`, `.venv/`, `__pycache__/`, `*.pyc` or `data/campuscare.db`.
- Keep only fictional sample data in the CSV files.
- Review the staged file list before committing.

Suggested `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
data/campuscare.db
```

Check repository contents before publishing:

```powershell
git status
```

---

**Application:** CampusCare AI  
**Assignment:** Agentic AI Engineering — Assignment 1
