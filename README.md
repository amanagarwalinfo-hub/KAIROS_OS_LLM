# KAIROS — Offline AI Tutor for Operating Systems

> *"The AI is not allowed to calculate. A tested program solves the problem, the AI only explains it, and every number is verified before the student sees it."*

---

## 🌟 What is KAIROS?

Standard LLMs (ChatGPT, Claude, etc.) frequently make subtle numerical errors when calculating:
- **CPU Scheduling** (SRTF, Round Robin, SJF waiting & turnaround times)
- **Virtual Memory** (Page faults in FIFO, LRU, Optimal)
- **Deadlock Avoidance** (Banker's Algorithm safe sequence & resource requests)
- **Disk Scheduling** (SCAN, C-LOOK head movements)

**KAIROS solves this fundamentally by adopting an Agentic Split Architecture:**
1. **The Language Model reads and structures the question.**
2. **The `os-solver` Python library deterministically calculates the exact math**, state transitions, and Gantt charts.
3. **The Answer Builder formats the pedagogical explanation** with analogies and syllabus references.
4. **The Checker (Verifier)** guarantees that 100% of the numbers in the explanation match the solver output.
5. **The Serving Layer itself runs on Operating System concepts** (MLFQ request scheduling, Clock page cache, Semaphores).

---

## 🏗️ Architecture

```
                      +-----------------------------+
                      |      STUDENT / TEACHER      |
                      +--------------+--------------+
                                     v
                      +-----------------------------+
                      |   L1 INTERFACE (Web / UI)   |
                      +--------------+--------------+
                                     v
                      +-----------------------------+
                      |    L2 ROUTER & EXTRACTOR    |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               v                                           v
    [ Numerical Path ]                             [ Theory / RAG Path ]
               v                                           v
    +----------------------+                       +----------------------+
    |  L4: OS SOLVER       |                       |  L4: HYBRID SEARCH   |
    |  - Scheduling (SRTF) |                       |  - OSTEP Notes       |
    |  - LRU / FIFO / Opt  |                       |  - xv6 code          |
    |  - Banker's Safety   |                       |  - BM25 + Dense RAG  |
    +----------+-----------+                       +----------+-----------+
               +---------------------+---------------------+
                                     v
                      +-----------------------------+
                      |     L5: ANSWER BUILDER      |
                      +--------------+--------------+
                                     v
                      +-----------------------------+
                      |      L6: LANGUAGE MODEL     |
                      |   (Teacher style & analogy) |
                      +--------------+--------------+
                                     v
                      +-----------------------------+
                      |    L7: CHECKER (VERIFIER)   |
                      |   (Match every single digit)|
                      +--------------+--------------+
                                     v
                      +-----------------------------+
                      |      L8: TEACHING LAYER     |
                      |  - Learn Mode vs Test Mode  |
                      |  - Follow-up challenge Qs   |
                      +-----------------------------+
```

---

## 🚀 How to Run KAIROS

### 1. Requirements
- Python 3.10+
- Installed packages: `fastapi`, `uvicorn`, `pydantic`, `pytest`

### 2. Run Automated Unit Tests (100% Coverage on Solvers)
```bash
cd backend
python -m pytest tests/test_solvers.py
```

### 3. Start the Server
```bash
cd backend
copy .env.example .env
# Edit .env and set GROQ_API_KEY to your own Groq API key.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Textbook-grounded answer generation (Groq)
Set `GROQ_API_KEY` in `backend/.env`. KAIROS sends retrieved textbook passages to Groq's chat-completions API for a student-friendly explanation. The default model is `openai/gpt-oss-20b`; optionally set `GROQ_MODEL` or `GROQ_MAX_OUTPUT_TOKENS` (default `450`, capped at `500`). The backend uses a single request with an 18-second timeout and falls back to the retrieved course material if generation is unavailable. Restart the backend after changing these settings.

### 4. Open the Interactive Web Tutor
Open your browser and navigate to:
```
http://127.0.0.1:8000/static/index.html
```

### Textbook files
The textbook PDFs and generated `indexed_book.json` are local-only and are not included in this public repository. To use your own licensed course materials, place PDFs in `backend/app/rag/data/` and rebuild the index with `python app/rag/pdf_indexer.py` from the `backend` directory.

---

## 🎯 Key Differentiators (For Presentation / Viva)

1. **Deterministic Accuracy**: Not relying on LLM token probabilities for arithmetic.
2. **Two Operating Modes**:
   - **Learn Mode**: Delivers comprehensive step-by-step explanations, Gantt timelines, and formulas.
   - **Test Mode**: Suppresses final solutions and offers guided pedagogical hints for lab exams.
3. **OS Engine**: The server's request scheduler simulates an **MLFQ** queue, while response caching uses the **Clock / Second-Chance** page replacement algorithm.

## HEISENBUG

Select **HEISENBUG** in the tutor's mode switch to practice finding exactly one deliberate error in solver-checked OS challenges. It covers CPU scheduling, deadlocks, memory management, page replacement, and process synchronization at easy, medium, and hard levels. Students can request three progressive hints, submit a diagnosis with reasoning and correction, and review the verified solution. Attempts, accuracy, hint usage, and recurring misconception topics are stored locally in SQLite and used to focus future challenges.
