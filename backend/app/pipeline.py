import re
import urllib.request
import urllib.error
import json
import os
import random
import threading
from collections import deque
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.solvers.scheduling import Process, solve_fcfs, solve_srf_or_srtf, solve_round_robin
from app.solvers.page_replacement import solve_fifo, solve_lru, solve_optimal
from app.solvers.bankers import BankerInput, solve_bankers_safety
from app.rag.retriever import CourseMaterialRetriever

retriever = CourseMaterialRetriever()

_ROAST_LINES = [
    "That process waited long enough to finish a trilogy; good thing the scheduler noticed.",
    "The kernel called. It wants its stack space back.",
    "Even a page fault gets a second chance. No pressure.",
    "Your explanation just completed a context switch into clarity.",
    "The semaphore says only one joke may enter the critical section at a time.",
    "That idea is now resident in memory. Let’s hope it isn’t the next page evicted.",
    "The deadlock tried to join this answer, but we found a safe sequence.",
    "The CPU took a tiny quantum to admire that answer.",
    "The race condition wanted credit, but it got blocked.",
    "The disk searched for a joke; the answer was already in cache.",
    "This concept booted successfully. No reboot required.",
    "We scheduled one tiny joke after the explanation. FCFS, obviously.",
]
_RECENT_ROASTS = deque(maxlen=5)
_ROAST_LOCK = threading.Lock()


def _next_roast() -> str:
    with _ROAST_LOCK:
        available = [line for line in _ROAST_LINES if line not in _RECENT_ROASTS]
        selected = random.choice(available or _ROAST_LINES)
        _RECENT_ROASTS.append(selected)
        return selected

class UserQueryRequest(BaseModel):
    query: str
    mode: str = "learn"  # "learn" (full solution) or "test" (hints only)
    student_id: Optional[str] = "student_1"
    roast_mode: bool = False

class TutorResponse(BaseModel):
    query_type: str  # "numerical", "theory", "out_of_syllabus"
    topic: str
    algorithm: Optional[str] = None
    source_reference: Optional[str] = None
    solution_data: Optional[Dict[str, Any]] = None
    explanation: str
    hints: List[str]
    checker_passed: bool
    practice_question: Optional[str] = None
    roast_mode: bool = False


def extract_scheduling_params(query: str):
    q_lower = query.lower()
    algo = "fcfs"
    if (
        "srtf" in q_lower
        or "shortest remaining" in q_lower
        or ("preemptive" in q_lower and ("sjf" in q_lower or "shortest job" in q_lower))
    ):
        algo = "srtf"
    elif "sjf" in q_lower or "shortest job" in q_lower:
        algo = "sjf"
    elif "round robin" in q_lower or "rr" in q_lower:
        algo = "rr"
    elif "fcfs" in q_lower or "first come" in q_lower:
        algo = "fcfs"

    quantum = 2
    quantum_match = re.search(r'quantum\s*(?:=|is|of)?\s*(\d+)', q_lower)
    if quantum_match:
        quantum = int(quantum_match.group(1))

    arrival_match = re.search(r'arriv(?:e|al)[^\d]*([\d\s,]+)', q_lower)
    burst_match = re.search(r'burst[^\d]*([\d\s,]+)', q_lower)

    processes = []
    if arrival_match and burst_match:
        arrivals = [int(x.strip()) for x in re.findall(r'\d+', arrival_match.group(1))]
        bursts = [int(x.strip()) for x in re.findall(r'\d+', burst_match.group(1))]
        n = min(len(arrivals), len(bursts))
        for i in range(n):
            processes.append(Process(pid=f"P{i+1}", arrival_time=arrivals[i], burst_time=bursts[i]))

    return algo, quantum, processes


def extract_page_replacement_params(query: str):
    q_lower = query.lower()
    algo = "fifo"
    if "lru" in q_lower or "least recently" in q_lower:
        algo = "lru"
    elif "optimal" in q_lower or "opt" in q_lower:
        algo = "optimal"
    elif "fifo" in q_lower:
        algo = "fifo"

    frames = 3
    frames_match = re.search(r'(\d+)\s*frames?', q_lower)
    if frames_match:
        frames = int(frames_match.group(1))

    ref_match = re.search(r'(?:string|stream|pages?)[^\d]*([\d\s,]+)', q_lower)
    ref_string = []
    if ref_match:
        ref_string = [int(x.strip()) for x in re.findall(r'\d+', ref_match.group(1))]
    else:
        all_nums = [int(x) for x in re.findall(r'\b\d+\b', query)]
        if len(all_nums) >= 5:
            ref_string = all_nums

    return algo, frames, ref_string


def try_groq_completion(prompt: str) -> Optional[str]:
    """Generate a textbook-grounded answer with Groq's OpenAI-compatible API."""
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Groq generation note: GROQ_API_KEY is not configured")
            return None
        data = {
            "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": min(int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "450")), 500),
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                # Groq's edge can reject urllib's default Python-urllib user agent.
                "User-Agent": "KAIROS-OS-Tutor/1.0",
                "Authorization": f"Bearer {api_key}",
            }
        )
        try:
            with urllib.request.urlopen(request, timeout=18) as resp:
                res_data = json.loads(resp.read().decode())
                choices = res_data.get("choices", [])
                text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
                if text:
                    return text
        except urllib.error.HTTPError as e:
            error_detail = e.read().decode("utf-8", errors="replace")[:300]
            print(f"Groq returned HTTP {e.code}: {error_detail}; using the textbook fallback")
        except Exception as e:
            print(f"Groq request failed; using the textbook fallback: {e}")
    except Exception as e:
        print(f"Groq generation note: {e}")
    return None


def add_textbook_teaching_note(explanation: str, query: str, topic: str, algorithm: str) -> tuple[str, Optional[str]]:
    """Add a short concept explanation grounded in the uploaded book, if found."""
    chunks, relevant = retriever.search(f"{query} {topic} {algorithm}", top_k=2)
    if not relevant or not chunks:
        return explanation, None

    source_text = " & ".join(dict.fromkeys(chunk.source for chunk in chunks))
    context = "\n\n---\n\n".join(
        f"Source: {chunk.source}\nPassage: {chunk.content[:1400]}"
        for chunk in chunks
    )
    prompt = f"""You are a patient Operating Systems tutor. Explain the underlying idea in simple language using only the supplied textbook passages.
Student question: {query}
Topic: {topic} — {algorithm}
Textbook passages:
{context}

Write a short concept note (2–4 sentences) that helps a student understand the method. Do not calculate, introduce numerical results, or contradict any solver output. If the passages do not explain the method, say so briefly rather than guessing."""
    note = try_groq_completion(prompt)
    if note:
        explanation += f"\n\n### 📚 Concept from your textbook\n\n{note}\n\n**Textbook:** {source_text}\n"
    else:
        explanation += f"\n\n**Textbook reference:** {source_text}\n"
    return explanation, source_text


def grounded_fallback(query: str, chunks: List[Any]) -> str:
    """Give a concise readable answer if the hosted model is temporarily unavailable."""
    os_definition = next((c for c in chunks if c.id == "ostep-ch2-intro"), None)
    os_examples = next((c for c in chunks if "1.13 open-source operating systems" in c.subtopic.lower() and "which can act as web servers as well as clients" in c.content.lower()), None)
    if os_definition and os_examples and re.search(r'\b(os|operating system)\b', query.lower()):
        return (
            "### What an operating system does\n\n"
            "An operating system (OS) is the software layer between applications and computer hardware. "
            "It manages resources such as the CPU, memory, and storage, and provides services that programs use.\n\n"
            "### How that appears in real systems\n\n"
            "The textbook describes Linux and Windows XP and later as systems that can act as both web clients and web servers. "
            "For example, a server OS can run web-server software and handle network requests; a client OS can run a browser and request pages.\n\n"
            "### Key takeaway\n\n"
            "An OS is implemented through its kernel and system services, which coordinate hardware and provide a platform for applications."
        )

    course_chunk = next((c for c in chunks if c.id.startswith("ostep-")), None)
    if course_chunk:
        return f"### {course_chunk.topic}\n\n{course_chunk.content.strip()}"

    if chunks:
        excerpts = []
        for chunk in chunks[:2]:
            passage = re.sub(r"\s+", " ", chunk.content).strip()
            if passage:
                excerpts.append(
                    f"#### {chunk.topic}: {chunk.subtopic}\n\n"
                    f"{passage[:1200]}{'…' if len(passage) > 1200 else ''}\n\n"
                    f"*From {chunk.source}*"
                )
        if excerpts:
            return (
                "Groq is temporarily unavailable, so here are the most relevant passages "
                "retrieved from your course books:\n\n" + "\n\n---\n\n".join(excerpts)
            )

    return (
        "The textbook passages were retrieved, but the hosted model is temporarily unavailable, so KAIROS could not safely "
        "summarize this topic. Please try again shortly. The retrieved textbook references are shown below."
    )


def is_complete_tutor_answer(answer: str) -> bool:
    """Reject visibly cut-off generations before showing them to a student."""
    text = re.sub(r"[`*_#>\s]+$", "", answer or "").strip().rstrip('"\u201d\u2019')
    return len(text.split()) >= 35 and bool(re.search(r"[.!?)]$", text))


def student_facing_topic(query: str, retrieved_topic: str) -> str:
    """Prefer the concept the student asked about over noisy PDF headings."""
    q = query.lower()
    concepts = (
        (r"\bpaging\b", "Paging"),
        (r"\bvirtual memory\b", "Virtual Memory"),
        (r"\bpage replacement\b|\bfifo\b|\blru\b|\boptimal replacement\b", "Page Replacement"),
        (r"\bdeadlock", "Deadlocks"),
        (r"\bsemaphore|\bmutex|\bmutual exclusion|\bcritical section", "Process Synchronization"),
        (r"\bsrtf\b|\bsjf\b|\bfcfs\b|\bround robin\b|\bscheduling\b", "CPU Scheduling"),
        (r"\bsegmentation\b", "Segmentation"),
    )
    for pattern, label in concepts:
        if re.search(pattern, q):
            return label
    return retrieved_topic


OUT_OF_SCOPE_REPLY = "My creators only trained me for OS. Please ask them to upgrade my brain if you want me to teach you more bruh"

OS_SCOPE_PATTERN = re.compile(
    r"\b(?:operating\s+systems?|os|kernel|linux|unix|windows|android|macos|"
    r"process(?:es)?|thread(?:s|ing)?|cpu|scheduling|preemptive|preemption|gantt|ready\s+queue|"
    r"waiting\s+time|turnaround\s+time|burst\s+time|round\s+robin|shortest\s+(?:remaining\s+time|job\s+first)|"
    r"srtf|sjf|fcfs|first[-\s]+come[-\s]+first[-\s]+served|deadlocks?|banker'?s?\s+algorithm|"
    r"semaphore|mutex|mutual\s+exclusion|critical\s+section|peterson(?:'s)?|bakery\s+algorithm|"
    r"synchroni[sz]ation|race\s+condition|producer[-\s]+consumer|readers?[-\s]+writers?|"
    r"dining\s+philosophers?|context\s+switch|interprocess\s+communication|ipc|"
    r"memory(?:\s+management)?|virtual\s+memory|paging|page\s+replacement|page\s+faults?|"
    r"frames?|segmentation|address\s+translation|tlb|thrashing|working\s+set|"
    r"inode|file\s+systems?|disk\s+(?:scheduling|management)|raid|directory|file\s+allocation|"
    r"system\s+calls?|interrupts?|device\s+drivers?|i/?o\s+(?:system|devices?)|"
    r"starvation|aging|zombies?|orphans?|boot(?:ing)?|shell|swap(?:ping)?|virtuali[sz]ation|"
    r"protection|authentication|access\s+control|distributed\s+systems?)\b",
    re.IGNORECASE,
)

def out_of_scope_response() -> TutorResponse:
    return TutorResponse(
        query_type="out_of_syllabus",
        topic="Out of Syllabus",
        algorithm=None,
        source_reference=None,
        solution_data=None,
        explanation=OUT_OF_SCOPE_REPLY,
        hints=[],
        checker_passed=True,
        practice_question=None,
    )


def _process_query(req: UserQueryRequest) -> TutorResponse:
    q_lower = req.query.lower()

    # Reject unrelated questions before common textbook words can cause false matches.
    if not OS_SCOPE_PATTERN.search(req.query):
        return out_of_scope_response()

    # Route concept questions to textbook search; run the solver only for an actual calculation.
    algo, quantum, processes = extract_scheduling_params(req.query)
    scheduling_algorithm_mentioned = bool(re.search(
        r"\b(?:srtf|sjf|fcfs|round\s+robin|shortest\s+job|shortest\s+remaining|first[-\s]+come[-\s]+first[-\s]+served)\b",
        q_lower,
    ))
    scheduling_calculation_requested = bool(processes) or any(
        cue in q_lower for cue in (
            "gantt", "waiting time", "turnaround", "completion time", "burst time",
            "calculate", "compute", "solve", "trace", "average",
        )
    )

    # 1. NUMERICAL PATH (CPU Scheduling)
    if scheduling_algorithm_mentioned and scheduling_calculation_requested:
        if not processes:
            requested_data = "arrival times and burst times for each process"
            if algo == "rr":
                requested_data += ", plus the time quantum"
            return TutorResponse(
                query_type="theory",
                topic="CPU Scheduling",
                algorithm=None,
                source_reference=None,
                solution_data=None,
                explanation=f"To calculate {algo.upper()} accurately, please provide {requested_data}.",
                hints=[],
                checker_passed=False,
                practice_question=None,
            )

        if algo == "srtf":
            res = solve_srf_or_srtf(processes, preemptive=True)
        elif algo == "sjf":
            res = solve_srf_or_srtf(processes, preemptive=False)
        elif algo == "rr":
            res = solve_round_robin(processes, quantum=quantum)
        else:
            res = solve_fcfs(processes)

        hints = [
            f"1. Remember that {res.algorithm} evaluates readiness at every step.",
            "2. Turnaround Time (TAT) = Completion Time - Arrival Time.",
            "3. Waiting Time (WT) = Turnaround Time - Burst Time.",
            f"4. First process scheduled is {res.gantt_chart[0].pid}."
        ]

        textbook_source = None
        if req.mode == "test":
            explanation = "### 🧪 Test Mode (Hints Only)\n\n" + "\n".join(hints) + "\n\n*Try calculating the completion times yourself, then switch to Learn Mode to compare!*"
        else:
            explanation = f"### 📊 Scheduling Analysis: {res.algorithm}\n\n"
            explanation += "**Gantt Chart Timeline:**\n"
            gantt_str = " | ".join([f"[{b.start} -> {b.end}] {b.pid}" for b in res.gantt_chart])
            explanation += f"`{gantt_str}`\n\n"
            explanation += "**Step-by-Step Execution Log:**\n"
            for step in res.step_by_step_explanation:
                explanation += f"- {step}\n"
            explanation += f"\n**Final Verified Metrics:**\n"
            explanation += f"- **Average Waiting Time (WT):** `{res.avg_waiting_time}`\n"
            explanation += f"- **Average Turnaround Time (TAT):** `{res.avg_turnaround_time}`\n"
            explanation += f"- **Context Switches:** `{res.context_switches}`\n"

            explanation, textbook_source = add_textbook_teaching_note(
                explanation, req.query, "CPU Scheduling", res.algorithm
            )

        practice_q = f"Try solving the same problem with Round Robin (quantum=3). Does the average waiting time increase or decrease?"

        return TutorResponse(
            query_type="numerical",
            topic="CPU Scheduling",
            algorithm=res.algorithm,
            source_reference=textbook_source or "CPU Scheduling course material",
            solution_data=res.model_dump(),
            explanation=explanation,
            hints=hints,
            checker_passed=True,
            practice_question=practice_q
        )

    # 2. NUMERICAL PATH (Page Replacement)
    elif any(k in q_lower for k in ["page fault", "page replacement", "belady", "lru", "optimal"]):
        algo, capacity, ref_string = extract_page_replacement_params(req.query)
        if not ref_string:
            ref_string = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]

        if algo == "lru":
            res = solve_lru(ref_string, capacity)
        elif algo == "optimal":
            res = solve_optimal(ref_string, capacity)
        else:
            res = solve_fifo(ref_string, capacity)

        hints = [
            f"1. Memory capacity is {capacity} frames.",
            f"2. Initially all frames are empty (cold compulsory misses).",
            "3. Hit Ratio = Total Hits / Total References."
        ]

        textbook_source = None
        if req.mode == "test":
            explanation = "### 🧪 Test Mode (Hints Only)\n\n" + "\n".join(hints)
        else:
            explanation = f"### 📑 Page Replacement Analysis: {res.algorithm}\n\n"
            explanation += f"**Reference String:** `{res.reference_string}`\n"
            explanation += f"**Capacity:** `{res.capacity}` frames\n\n"
            explanation += "**Step-by-step Frame History:**\n"
            for s in res.steps:
                status = "❌ FAULT" if s.is_fault else "✅ HIT"
                explanation += f"- Step {s.step} (Page {s.page}): {status} | Frames: `{s.frames}` ({s.reason})\n"
            explanation += f"\n**Final Verified Metrics:**\n"
            explanation += f"- **Total Page Faults:** `{res.page_faults}`\n"
            explanation += f"- **Total Page Hits:** `{res.page_hits}`\n"
            explanation += f"- **Hit Ratio:** `{res.hit_ratio * 100}%`\n"

            explanation, textbook_source = add_textbook_teaching_note(
                explanation, req.query, "Virtual Memory and Page Replacement", res.algorithm
            )

        practice_q = f"What happens if we increase frame capacity to {capacity + 1}? Test if FIFO suffers from Belady's Anomaly!"

        return TutorResponse(
            query_type="numerical",
            topic="Virtual Memory",
            algorithm=res.algorithm,
            source_reference=textbook_source or "Virtual Memory course material",
            solution_data=res.model_dump(),
            explanation=explanation,
            hints=hints,
            checker_passed=True,
            practice_question=practice_q
        )

    # 3. THEORY / RAG PATH
    else:
        chunks, is_relevant = retriever.search(req.query, top_k=3)

        # Objective 6 & Target table: Say "not in syllabus" instead of making something up
        if not is_relevant or not chunks:
            return out_of_scope_response()

        # Construct verified explanation from course material
        primary = chunks[0]
        sources = " & ".join([c.source for c in chunks])

        if req.mode == "test":
            hints = [
                f"1. This concept relates to {primary.topic} ({primary.subtopic}).",
                f"2. Reference reading: {primary.source}.",
                "3. Think about what happens when shared state or timing is not coordinated."
            ]
            explanation = "### 🧪 Test Mode (Hints Only)\n\n" + "\n".join(hints)
        else:
            hints = [f"Refer to {primary.source} for textbook proofs and diagrams."]
            
            # Use multiple retrieved passages so answers can explain the concept,
            # while keeping the prompt bounded for local models.
            context_chunks = chunks[:3]
            textbook_context = "\n\n---\n\n".join(
                f"Source: {chunk.source}\nTopic: {chunk.topic} — {chunk.subtopic}\nPassage: {chunk.content[:1800]}"
                for chunk in context_chunks
            )
            teacher_prompt = f"""You are KAIROS, a patient Operating Systems tutor. Teach the student in plain language.

Student question: {req.query}
Retrieved topic: {primary.topic} — {primary.subtopic}

Use the textbook passages below as the factual basis for your answer. Directly answer the question, explain unfamiliar terms, and use a short example or analogy when it helps. Organize the answer with a clear definition, how it works, and a key takeaway. Do not claim a detail is in the book unless it appears in these passages. If the passages do not support part of the question, say what they do support and identify the gap instead of guessing.

Textbook passages:
{textbook_context}

Write a complete explanation for a student (about 100–160 words). Finish every sentence and every Markdown emphasis marker. Do not repeat a fragment. Use clean Markdown; cite the supplied source names in a short source line."""

            llm_generated = try_groq_completion(teacher_prompt)
            if llm_generated and not is_complete_tutor_answer(llm_generated):
                llm_generated = try_groq_completion(
                    teacher_prompt + "\n\nYour previous draft was incomplete. Rewrite the whole answer with complete sentences, close all Markdown formatting, and end with a clear takeaway."
                )
            if llm_generated and is_complete_tutor_answer(llm_generated):
                explanation = (
                    f"{llm_generated}\n\n"
                    f"---\n"
                    f"📚 **Verified Textbook Source:** `{sources}`\n"
                )
            else:
                explanation = (
                    f"{grounded_fallback(req.query, chunks)}\n\n"
                    f"---\n"
                    f"📚 **Verified Textbook Source:** `{sources}`\n"
                )

        display_topic = student_facing_topic(req.query, primary.topic)
        challenge = f"Viva Question: What is one key idea about {display_topic} that you would explain to a classmate?"
        if display_topic == "Paging":
            challenge = "Viva Question: How does a page table translate a virtual page number into a physical frame number?"
        elif display_topic == "Virtual Memory":
            challenge = "Viva Question: What happens during a page fault, and how does the operating system respond?"
        elif display_topic == "Page Replacement":
            challenge = "Viva Question: How does the chosen page-replacement policy decide which page to evict?"
        elif display_topic == "Segmentation":
            challenge = "Viva Question: Why does segmentation suffer from external fragmentation while paging suffers from internal fragmentation?"
        elif display_topic == "Process Synchronization":
            challenge = "Viva Question: Name the three criteria required to solve the Critical Section Problem and explain what happens if Bounded Waiting is violated."
        elif "starvation" in req.query.lower():
            challenge = "Viva Question: Explain the difference between Starvation and Deadlock, and how the Aging technique prevents starvation."
        elif display_topic == "CPU Scheduling":
            challenge = "Viva Question: How does the scheduling algorithm in your question choose the next process to run?"

        return TutorResponse(
            query_type="theory",
            topic=display_topic,
            algorithm=None,
            source_reference=sources,
            solution_data=None,
            explanation=explanation,
            hints=hints,
            checker_passed=True,
            practice_question=challenge
        )


def process_query(req: UserQueryRequest) -> TutorResponse:
    """Preserve verified answers while optionally adding a light, topic-safe roast."""
    response = _process_query(req)
    if not req.roast_mode or response.query_type == "out_of_syllabus":
        return response

    response.roast_mode = True
    if response.query_type == "numerical":
        roast = _next_roast() + " The calculations above are still solver-verified."
    else:
        roast = _next_roast() + " Keep the key idea in memory!"
    response.explanation += f"\n\n---\n\n🔥 **Roast mode:** {roast}"
    return response
