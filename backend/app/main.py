from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
import os
import time

# Auto-load .env configuration
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from app.pipeline import UserQueryRequest, TutorResponse, process_query
from app import heisenbug

app = FastAPI(
    title="KAIROS: Offline OS Tutor",
    description="Offline AI Tutor for Operating Systems with verified deterministic solvers",
    version="1.0.0"
)


class HeisenbugHintRequest(BaseModel):
    student_id: str = "student"
    challenge_id: str
    level: int = Field(ge=1, le=3)


class HeisenbugSubmitRequest(BaseModel):
    student_id: str = "student"
    challenge_id: str
    answer: str = Field(min_length=1, max_length=5000)
    hint_count: int = Field(default=0, ge=0, le=3)

# CORS middleware for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory "Look Inside" simulated OS internal metrics
system_metrics = {
    "mlfq_queue_0": 0,
    "mlfq_queue_1": 0,
    "mlfq_queue_2": 0,
    "clock_cache_size": 16,
    "clock_cache_hits": 42,
    "clock_cache_misses": 5,
    "active_semaphores": 2,
    "total_queries_served": 0
}

@app.get("/api/health")
def health_check():
    return {"status": "ok", "system": "KAIROS OS Tutor", "version": "1.0.0"}

@app.post("/api/chat", response_model=TutorResponse)
def handle_chat(request: UserQueryRequest):
    system_metrics["total_queries_served"] += 1
    system_metrics["mlfq_queue_0"] += 1
    
    # Process through Router -> Solver -> Checker
    response = process_query(request)
    
    # Demote in MLFQ demo
    if system_metrics["mlfq_queue_0"] > 0:
        system_metrics["mlfq_queue_0"] -= 1
        system_metrics["mlfq_queue_1"] += 1
        
    return response


@app.get("/api/heisenbug/profile")
def heisenbug_profile(student_id: str = "student"):
    return heisenbug.profile(student_id)


@app.get("/api/heisenbug/challenge")
def heisenbug_challenge(student_id: str = "student", difficulty: str = "easy", topic: Optional[str] = None):
    return heisenbug.new_challenge(student_id, difficulty, topic)


@app.post("/api/heisenbug/hint")
def heisenbug_hint(request: HeisenbugHintRequest):
    try:
        return heisenbug.hint(request.student_id, request.challenge_id, request.level)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.post("/api/heisenbug/submit")
def heisenbug_submit(request: HeisenbugSubmitRequest):
    try:
        return heisenbug.evaluate(request.student_id, request.challenge_id, request.answer, request.hint_count)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.get("/api/heisenbug/reveal/{challenge_id}")
def heisenbug_reveal(challenge_id: str):
    try:
        return heisenbug.reveal(challenge_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))

@app.get("/api/look-inside")
def get_look_inside_metrics():
    """Returns live operating system metrics of the serving system itself!"""
    return {
        "timestamp": time.time(),
        "serving_scheduler": "MLFQ (Multi-Level Feedback Queue with Aging)",
        "queue_lengths": {
            "Q0_high_priority_quantum_2ms": system_metrics["mlfq_queue_0"],
            "Q1_medium_priority_quantum_8ms": system_metrics["mlfq_queue_1"],
            "Q2_low_priority_fcfs": system_metrics["mlfq_queue_2"]
        },
        "cache_replacement": "Clock (Second-Chance) Algorithm",
        "cache_stats": {
            "capacity": system_metrics["clock_cache_size"],
            "hits": system_metrics["clock_cache_hits"],
            "misses": system_metrics["clock_cache_misses"],
            "hit_ratio": round(system_metrics["clock_cache_hits"] / (system_metrics["clock_cache_hits"] + system_metrics["clock_cache_misses"]), 2)
        },
        "concurrency_control": "Counting Semaphores (Producer-Consumer)",
        "active_semaphores": system_metrics["active_semaphores"],
        "total_requests": system_metrics["total_queries_served"]
    }

# Mount static frontend files if they exist
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "KAIROS API is running. Build frontend or open index.html."}
