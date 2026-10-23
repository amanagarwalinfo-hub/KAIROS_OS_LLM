"""Solver-backed HEISENBUG challenges and per-student progress tracking."""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.pipeline import try_groq_completion
from app.solvers.scheduling import Process, solve_fcfs, solve_srf_or_srtf, solve_round_robin
from app.solvers.page_replacement import solve_fifo, solve_lru, solve_optimal
from app.solvers.bankers import BankerInput, solve_bankers_safety


DB_PATH = os.path.join(os.path.dirname(__file__), "data", "heisenbug_progress.sqlite3")
DIFFICULTIES = ("easy", "medium", "hard")


def _challenge(cid: str, topic: str, difficulty: str, title: str, prompt: str,
               correct_lines: List[str], error_index: int, incorrect_line: str,
               correction: str, explanation: str, hints: List[str],
               diagnosis_groups: List[List[str]], correction_groups: List[List[str]],
               reasoning_groups: List[List[str]], misconception: str) -> Dict[str, Any]:
    if len(correct_lines) < 1 or not 0 <= error_index < len(correct_lines):
        raise ValueError(f"Invalid challenge definition: {cid}")
    lines = list(correct_lines)
    lines[error_index] = incorrect_line
    # Authoring guard: the displayed challenge must contain exactly one changed line.
    if sum(a != b for a, b in zip(lines, correct_lines)) != 1:
        raise ValueError(f"Challenge {cid} must contain exactly one intentional error")
    return {
        "id": cid, "topic": topic, "difficulty": difficulty, "title": title,
        "prompt": prompt, "lines": lines, "correct_lines": correct_lines,
        "error_index": error_index, "incorrect_line": incorrect_line,
        "correction": correction, "explanation": explanation, "hints": hints,
        "diagnosis_groups": diagnosis_groups, "correction_groups": correction_groups,
        "reasoning_groups": reasoning_groups, "misconception": misconception,
    }


def _scheduling_challenge(difficulty: str) -> Dict[str, Any]:
    if difficulty == "easy":
        processes = [Process(pid="P1", arrival_time=0, burst_time=4), Process(pid="P2", arrival_time=1, burst_time=3)]
        result = solve_fcfs(processes)
        target = next(m for m in result.process_metrics if m.pid == "P2")
        correct = [f"{m.pid}: CT={m.completion_time}, TAT={m.turnaround_time}, WT={m.waiting_time}" for m in result.process_metrics]
        index = 1
        wrong = f"P2: CT={target.completion_time}, TAT={target.turnaround_time}, WT={target.waiting_time - 1}"
        return _challenge("cpu-fcfs-easy", "CPU scheduling", difficulty, "FCFS waiting-time check",
            "P1 arrives at 0 with burst 4; P2 arrives at 1 with burst 3. One reported metric is wrong.",
            correct, index, wrong, f"P2 waiting time is {target.waiting_time} time units.",
            f"Waiting time is TAT − burst time. For P2: {target.turnaround_time} − 3 = {target.waiting_time}.",
            ["Start with P2's turnaround time.", "Use WT = TAT − burst time.", "P2's verified waiting time is " + str(target.waiting_time) + "."],
            [["p2"], ["waiting time", "wt"]], [[str(target.waiting_time)]], [["turnaround", "tat"], ["burst"]], "waiting-time formula")
    processes = [Process(pid="P1", arrival_time=0, burst_time=7), Process(pid="P2", arrival_time=2, burst_time=4), Process(pid="P3", arrival_time=4, burst_time=1)]
    if difficulty == "medium":
        result = solve_srf_or_srtf(processes, preemptive=True)
        algorithm, cid = "SRTF", "cpu-srtf-medium"
    else:
        result = solve_round_robin(processes, quantum=2)
        algorithm, cid = "Round Robin (q=2)", "cpu-rr-hard"
    metric = "avg_waiting_time" if difficulty == "medium" else "avg_turnaround_time"
    label = "average waiting time" if difficulty == "medium" else "average turnaround time"
    correct_value = getattr(result, metric)
    correct = [f"Algorithm: {algorithm}", "Gantt: " + " | ".join(f"{b.start}-{b.end} {b.pid}" for b in result.gantt_chart), f"{label.title()}: {correct_value}"]
    wrong_value = round(correct_value + 1, 2)
    return _challenge(cid, "CPU scheduling", difficulty, f"{algorithm} trace audit",
        "The solver-generated trace is shown with one deliberately altered final metric.", correct, 2,
        f"{label.title()}: {wrong_value}", f"{label.title()} is {correct_value}.",
        f"The schedule is correct; check the formula for {label} and recompute it from the per-process results.",
        ["The Gantt chart is the verified trace; inspect the metric line.", "For waiting time, use TAT − burst. For turnaround, use completion − arrival.", f"The solver verifies {label} = {correct_value}."],
        [[label]], [[str(correct_value)]], [["completion", "arrival", "burst", "average", "mean"]], "scheduling metric formula")


def _deadlock_challenge(difficulty: str) -> Dict[str, Any]:
    if difficulty == "easy":
        data = BankerInput(processes=["P0", "P1"], resources=["A"], allocation=[[1], [1]], max_matrix=[[2], [1]], available=[0])
        result = solve_bankers_safety(data)
        correct = ["Available: A=0", "Need: P0=1, P1=0", "Safe sequence: " + " -> ".join(result.safe_sequence)]
        return _challenge("deadlock-bankers-easy", "Deadlocks", difficulty, "Banker's safety check",
            "One conclusion in this one-resource Banker's check is wrong.", correct, 2,
            "Safe sequence: P0 -> P1", "Safe sequence: P1 -> P0.",
            "A process can run only when Need ≤ Available; after it finishes, it releases its allocation.",
            ["Compare each process's Need with Available first.", "P0 needs one unit but Available is zero; P1 needs zero.", "Run P1 first, then P0."],
            [["safe sequence", "p0", "p1"]], [["p1", "p0"]], [["need", "available", "release", "allocation"]], "safe-sequence eligibility")
    if difficulty == "medium":
        data = BankerInput(
            processes=["P0", "P1", "P2", "P3", "P4"], resources=["A", "B", "C"],
            allocation=[[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
            max_matrix=[[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]], available=[3, 3, 2])
        result = solve_bankers_safety(data)
        conclusion = "System is safe." if result.is_safe else "System is unsafe."
        wrong = "System is unsafe." if result.is_safe else "System is safe."
        correction = f"{conclusion} Safe sequence: {' -> '.join(result.safe_sequence)}." if result.is_safe else conclusion
        return _challenge("deadlock-bankers-medium", "Deadlocks", difficulty, "Banker's multi-resource conclusion",
            "The allocation data is verified. Find the single incorrect safety conclusion.",
            ["Available: A=3, B=3, C=2", "Need = Max − Allocation", correction], 2, wrong,
            correction, "A state is safe if a sequence exists in which each process can finish with the available work plus resources released by completed processes.",
            ["A state is safe when at least one full completion order exists.", "Use Need = Max − Allocation, then compare each row with Work.", "The solver finds: " + " -> ".join(result.safe_sequence) + "."],
            [["unsafe", "safe"]], [["safe sequence", "p1"]], [["need", "work", "finish", "release", "sequence"]], "safe versus unsafe state")
    data = BankerInput(processes=["P0", "P1"], resources=["A"], allocation=[[1], [1]], max_matrix=[[3], [3]], available=[0])
    result = solve_bankers_safety(data)
    correct = ["Available: A=0", "Need: P0=2, P1=2", "System is unsafe; neither process can finish first."]
    return _challenge("deadlock-bankers-hard", "Deadlocks", difficulty, "Unsafe-state detection",
        "For this single-resource state, one safety claim is wrong.", correct, 2,
        "System is safe; P0 can finish first.", "System is unsafe; no process has Need ≤ Available.",
        "The safety algorithm needs at least one unfinished process whose need fits the current Work vector.",
        ["Compute Need = Max − Allocation.", "Compare each need with Available=0.", "No process can start, so no safe sequence exists."],
        [["safe", "p0"]], [["unsafe", "no process", "neither"]], [["need", "available", "finish", "sequence"]], "safe versus unsafe state")


def _memory_challenge(difficulty: str) -> Dict[str, Any]:
    if difficulty == "easy":
        page_size, logical, frame = 1024, 2500, 5
        page, offset = divmod(logical, page_size)
        physical = frame * page_size + offset
        return _challenge("memory-page-translation-easy", "Memory management", difficulty, "Paging address translation",
            f"Page size={page_size} bytes; logical address={logical}; page {page} maps to frame {frame}. One translation line is wrong.",
            [f"Page number={page}, offset={offset}", f"Physical address={physical}"], 1,
            f"Physical address={physical - 120}", f"Physical address={physical}.",
            "Split the logical address into page number and offset; preserve the offset when forming frame×page-size + offset.",
            ["Find quotient and remainder after dividing by the page size.", "The offset is the remainder; the physical address uses the same offset.", f"Compute {frame}×{page_size}+{offset}."],
            [["physical address"]], [[str(physical)]], [["frame", "offset", "page size", "remainder", "multiply", "add"]], "page-offset arithmetic")
    if difficulty == "medium":
        base, limit, offset = 4000, 1000, 1200
        return _challenge("memory-segmentation-medium", "Memory management", difficulty, "Segmentation bounds check",
            f"Segment base={base}, limit={limit}, requested offset={offset}. One translation result is wrong.",
            [f"Bounds rule: valid offsets are 0 through {limit - 1}.", "Access result: trap; no physical address is produced."], 1,
            f"Access result: valid; physical address={base + offset}.", "The offset exceeds the segment limit, so the CPU traps; no physical address is produced.",
            "In segmentation, check the offset against the segment limit before adding it to the base.",
            ["Check the requested offset against the limit first.", "An offset greater than or equal to the limit is invalid.", "This access traps; do not calculate a physical address."],
            [["physical address", "valid", "address"]], [["trap", "invalid", "exceeds", "limit"]], [["offset", "limit", "bounds", "before", "trap"]], "segment-bound violation")
    request, page_size = 5000, 4096
    pages = (request + page_size - 1) // page_size
    allocated = pages * page_size
    waste = allocated - request
    return _challenge("memory-internal-fragmentation-hard", "Memory management", difficulty, "Internal-fragmentation calculation",
        f"A process needs {request} bytes and pages are {page_size} bytes. One allocation result is wrong.",
        [f"Frames allocated: {pages}", f"Allocated bytes: {allocated}", f"Unused space in the last page: {waste} bytes"], 2,
        f"Unused space in the last page: {waste + 1000} bytes", f"Unused space in the last page: {waste} bytes.",
        "Internal fragmentation is the unused space inside the last allocated page: allocated bytes − requested bytes.",
        ["Round the process size up to a whole number of pages.", "Subtract requested bytes from total allocated bytes.", f"Compute {allocated} − {request}."],
        [["unused", "fragmentation", "waste"]], [[str(waste)]], [["allocated", "requested", "page", "subtract", "difference"]], "internal-fragmentation arithmetic")


def _page_challenge(difficulty: str) -> Dict[str, Any]:
    refs = [1, 2, 3, 1, 4]
    if difficulty == "easy":
        result = solve_fifo(refs, 3)
        step = result.steps[3]
        correct = [f"Step {s.step}, page {s.page}: {'FAULT' if s.is_fault else 'HIT'}; frames={s.frames}" for s in result.steps]
        return _challenge("page-fifo-easy", "Page replacement", difficulty, "FIFO hit-or-fault trace",
            "FIFO uses 3 frames for reference string 1, 2, 3, 1, 4. One trace entry is wrong.", correct, 3,
            f"Step {step.step}, page {step.page}: FAULT; frames={step.frames}",
            f"Step {step.step}, page {step.page} is a HIT; frames remain {step.frames}.",
            "A reference is a hit when that page is already resident in a frame.",
            ["Check whether the referenced page is already in the displayed frames.", "Page 1 was loaded at step 1 and has not been evicted yet.", "Step 4 is a hit, not a fault."],
            [["step 4", "page 1"]], [["hit"]], [["already", "frame", "resident", "loaded"]], "page hit versus fault")
    if difficulty == "medium":
        result = solve_lru(refs, 3)
        true_step = result.steps[4]
        wrong_frames = list(result.steps[3].frames)
        wrong_frames[wrong_frames.index(1)] = 4
        correct = [f"Step {s.step}, page {s.page}: {'FAULT' if s.is_fault else 'HIT'}; frames={s.frames}" for s in result.steps]
        wrong = f"Step 5, page 4: FAULT; evict page 1; frames={wrong_frames}"
        return _challenge("page-lru-medium", "Page replacement", difficulty, "LRU victim selection",
            "LRU uses 3 frames for reference string 1, 2, 3, 1, 4. One replacement entry is wrong.", correct, 4, wrong,
            f"At step 5, LRU evicts page {true_step.evicted_page}; frames become {true_step.frames}.",
            "LRU evicts the resident page whose most recent reference is farthest in the past.",
            ["At step 5, compare the last-use times of pages 1, 2, and 3.", "Page 1 was just used at step 4.", f"The least recently used page is {true_step.evicted_page}."],
            [["step 5", "page 4", "evict"]], [[str(true_step.evicted_page)]], [["recent", "last used", "step 4", "oldest"]], "LRU victim selection")
    refs = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
    result = solve_optimal(refs, 3)
    wrong_faults = result.page_faults + 1
    correct = [f"OPT page faults: {result.page_faults}", f"OPT page hits: {result.page_hits}"]
    return _challenge("page-optimal-hard", "Page replacement", difficulty, "Optimal page-fault total",
        f"Use 3 frames and the reference string {refs}. One reported total is wrong.", correct, 0,
        f"OPT page faults: {wrong_faults}", f"OPT page faults: {result.page_faults}; page hits: {result.page_hits}.",
        "On each fault, OPT evicts the page whose next use is farthest in the future, or that is never used again.",
        ["A hit does not change the frame set.", "On a fault, inspect future references for the resident pages.", f"The verified total is {result.page_faults} faults and {result.page_hits} hits."],
        [["page faults", "fault total", "faults"]], [[str(result.page_faults)]], [["future", "farthest", "next use", "never used"]], "optimal replacement look-ahead")


def _sync_challenge(difficulty: str) -> Dict[str, Any]:
    if difficulty == "easy":
        correct = ["flag[i] = true;", "turn = j;", "while (flag[j] && turn == j) { }", "critical_section();", "flag[i] = false;"]
        return _challenge("sync-peterson-easy", "Process synchronization", difficulty, "Peterson's algorithm",
            "This is process i's entry protocol. Exactly one line breaks Peterson's mutual-exclusion protocol.",
            correct, 1, "turn = i;", "Set turn = j before waiting.",
            "Peterson's algorithm uses intent flags and gives the other process priority when both want to enter.",
            ["Compare the assignment to the other process index j.", "The turn variable must yield priority to the other process.", "The incorrect line is `turn = i`; it should be `turn = j`."],
            [["turn", "priority"]], [["turn = j", "turn to j"]], [["other process", "j", "both", "priority", "wait"]], "Peterson turn variable")
    if difficulty == "medium":
        correct = ["wait(empty);", "wait(mutex);", "insert_item(item);", "signal(mutex);", "signal(full);"]
        return _challenge("sync-semaphore-medium", "Process synchronization", difficulty, "Producer semaphore ordering",
            "A bounded-buffer producer uses `empty` and `mutex`. One synchronization step is in the wrong order.",
            correct, 0, "wait(mutex);", "Wait on empty before acquiring mutex.",
            "The producer should wait for an empty slot before locking the shared buffer; this avoids holding the lock while blocked for space.",
            ["Which semaphore represents available buffer slots?", "A producer must not hold the mutex while waiting for an empty slot.", "Acquire `empty` before `mutex`."],
            [["order", "first", "before", "empty", "mutex"]], [["empty", "before", "mutex"]], [["blocked", "wait", "slot", "deadlock", "lock"]], "semaphore acquisition order")
    correct = ["CPU 0 reads lock=0.", "CPU 1 reads lock=0.", "CPU 0 writes lock=1.", "CPU 1 writes lock=1.", "Both processes enter the critical section."]
    return _challenge("sync-atomic-hard", "Process synchronization", difficulty, "Atomic lock trace",
        "The lock uses a separate read and write (not an atomic instruction). One conclusion in this execution trace is wrong.",
        correct, 4, "At most one process enters the critical section.",
        "Both processes can enter; use an atomic test-and-set or compare-and-swap to acquire the lock.",
        "Both CPUs read the old value before either writes it, so each believes the lock is free. A normal read and write do not guarantee mutual exclusion.",
        ["Compare both reads with the writes that follow.", "Each CPU sees lock=0 before either write happens.", "Both can enter; an atomic read-modify-write operation is required."],
        [["both", "processes", "enter"]], [["atomic", "test-and-set", "compare-and-swap"]], [["read", "write"], ["same time", "simultaneously", "race"]], "non-atomic check-and-set")


BUILDERS = {
    "CPU scheduling": _scheduling_challenge,
    "Deadlocks": _deadlock_challenge,
    "Memory management": _memory_challenge,
    "Page replacement": _page_challenge,
    "Process synchronization": _sync_challenge,
}
CHALLENGES: Dict[str, Dict[str, Any]] = {}
for builder in BUILDERS.values():
    for difficulty in DIFFICULTIES:
        item = builder(difficulty)
        CHALLENGES[item["id"]] = item


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, student_id TEXT NOT NULL, challenge_id TEXT NOT NULL, topic TEXT NOT NULL, difficulty TEXT NOT NULL, correct INTEGER NOT NULL, hint_count INTEGER NOT NULL, misconception TEXT, created_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS hint_events (id INTEGER PRIMARY KEY, student_id TEXT NOT NULL, challenge_id TEXT NOT NULL, hint_level INTEGER NOT NULL, created_at TEXT NOT NULL)")
    db.commit()
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _student_id(value: Optional[str]) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '', value or "student")[:80]
    return cleaned or "student"


def profile(student_id: Optional[str]) -> Dict[str, Any]:
    sid = _student_id(student_id)
    with _connect() as db:
        row = db.execute("SELECT COUNT(*) attempts, COALESCE(SUM(correct),0) correct, COALESCE(SUM(hint_count),0) hints FROM attempts WHERE student_id=?", (sid,)).fetchone()
        topics = db.execute("SELECT topic, COUNT(*) attempts, COALESCE(SUM(correct),0) correct, COALESCE(SUM(hint_count),0) hints FROM attempts WHERE student_id=? GROUP BY topic ORDER BY (1.0*SUM(correct)/COUNT(*)) ASC, attempts DESC", (sid,)).fetchall()
        misconceptions = db.execute("SELECT misconception, COUNT(*) occurrences FROM attempts WHERE student_id=? AND misconception IS NOT NULL GROUP BY misconception ORDER BY occurrences DESC LIMIT 3", (sid,)).fetchall()
    attempts = int(row["attempts"])
    return {
        "attempts": attempts,
        "correct": int(row["correct"]),
        "accuracy": round((int(row["correct"]) / attempts) * 100) if attempts else 0,
        "hint_uses": int(row["hints"]),
        "weakest_topic": topics[0]["topic"] if topics else None,
        "topics": [{"topic": t["topic"], "attempts": t["attempts"], "accuracy": round(100*t["correct"]/t["attempts"]), "hint_uses": t["hints"]} for t in topics],
        "misconceptions": [{"misconception": m["misconception"], "occurrences": m["occurrences"]} for m in misconceptions],
    }


def new_challenge(student_id: Optional[str], difficulty: str = "easy", topic: Optional[str] = None) -> Dict[str, Any]:
    sid = _student_id(student_id)
    if difficulty not in DIFFICULTIES:
        difficulty = "easy"
    prof = profile(sid)
    if topic not in BUILDERS:
        topic = prof["weakest_topic"] or random.choice(list(BUILDERS))
    candidates = [c for c in CHALLENGES.values() if c["topic"] == topic and c["difficulty"] == difficulty]
    selected = random.choice(candidates)
    public = {key: selected[key] for key in ("id", "topic", "difficulty", "title", "prompt", "lines")}
    public["progress"] = prof
    public["personalized_topic"] = topic
    return public


def hint(student_id: Optional[str], challenge_id: str, level: int) -> Dict[str, Any]:
    challenge = CHALLENGES.get(challenge_id)
    if not challenge:
        raise KeyError("Challenge not found")
    level = max(1, min(int(level), len(challenge["hints"])))
    with _connect() as db:
        db.execute("INSERT INTO hint_events(student_id, challenge_id, hint_level, created_at) VALUES(?,?,?,?)", (_student_id(student_id), challenge_id, level, _now()))
    return {"level": level, "total": len(challenge["hints"]), "hint": challenge["hints"][level - 1]}


def _has_group(text: str, choices: List[str]) -> bool:
    for choice in choices:
        value = choice.lower()
        if value.isdigit():
            if re.search(rf'(?<!\w){re.escape(value)}(?!\w)', text):
                return True
        elif value in text:
            return True
    return False


def evaluate(student_id: Optional[str], challenge_id: str, answer: str, hint_count: int) -> Dict[str, Any]:
    challenge = CHALLENGES.get(challenge_id)
    if not challenge:
        raise KeyError("Challenge not found")
    answer_text = answer.strip().lower()
    diagnosis_ok = all(_has_group(answer_text, group) for group in challenge["diagnosis_groups"])
    correction_ok = all(_has_group(answer_text, group) for group in challenge["correction_groups"])
    reasoning_ok = all(_has_group(answer_text, group) for group in challenge["reasoning_groups"])
    score = (35 if diagnosis_ok else 0) + (40 if correction_ok else 0) + (25 if reasoning_ok else 0)
    correct = score >= 75
    misconception = None if correct else challenge["misconception"]
    with _connect() as db:
        prior_hints = db.execute("SELECT COUNT(*) FROM hint_events WHERE student_id=? AND challenge_id=?", (_student_id(student_id), challenge_id)).fetchone()[0]
        used_hints = max(int(hint_count), int(prior_hints))
        db.execute("INSERT INTO attempts(student_id,challenge_id,topic,difficulty,correct,hint_count,misconception,created_at) VALUES(?,?,?,?,?,?,?,?)",
                   (_student_id(student_id), challenge_id, challenge["topic"], challenge["difficulty"], int(correct), used_hints, misconception, _now()))

    status = "Strong explanation." if correct else "Your answer is partly there; compare your reasoning with the verified correction below."
    llm_feedback = try_groq_completion(
        "You are giving brief formative feedback on an operating-systems error-detection exercise. "
        f"Challenge: {challenge['title']}\nStudent response: {answer[:1200]}\n"
        f"Verified diagnosis: {challenge['incorrect_line']}\nVerified correction: {challenge['correction']}\n"
        f"Verified explanation: {challenge['explanation']}\nProgrammatic rubric: diagnosis={'met' if diagnosis_ok else 'missing'}, correction={'met' if correction_ok else 'missing'}, reasoning={'met' if reasoning_ok else 'missing'}.\n"
        f"The program has determined correctness={correct}. Do not override that verdict. Give two concise sentences of constructive feedback."
    )
    return {
        "correct": correct, "score": score, "feedback": llm_feedback or status,
        "diagnosis_identified": diagnosis_ok, "correction_provided": correction_ok, "reasoning_explained": reasoning_ok,
        "solution": challenge["correction"], "explanation": challenge["explanation"],
        "misconception": misconception, "topic": challenge["topic"], "difficulty": challenge["difficulty"],
        "hint_count": used_hints,
        "followup": {"topic": challenge["topic"], "difficulty": "medium" if challenge["difficulty"] == "easy" else "hard" if correct and challenge["difficulty"] == "medium" else challenge["difficulty"]},
        "progress": profile(student_id),
    }


def reveal(challenge_id: str) -> Dict[str, str]:
    challenge = CHALLENGES.get(challenge_id)
    if not challenge:
        raise KeyError("Challenge not found")
    return {"solution": challenge["correction"], "explanation": challenge["explanation"]}

