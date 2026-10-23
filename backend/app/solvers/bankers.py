from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BankerInput(BaseModel):
    processes: List[str]  # e.g. ["P0", "P1", "P2", "P3", "P4"]
    resources: List[str]  # e.g. ["A", "B", "C"]
    allocation: List[List[int]]  # matrix [num_processes x num_resources]
    max_matrix: List[List[int]]  # matrix [num_processes x num_resources]
    available: List[int]        # vector [num_resources]

class SafetyResult(BaseModel):
    is_safe: bool
    safe_sequence: List[str]
    need_matrix: List[List[int]]
    work_history: List[Dict[str, Any]]
    explanation: List[str]

class RequestResult(BaseModel):
    can_grant: bool
    reason: str
    safety_after_grant: Optional[SafetyResult] = None
    explanation: List[str]


def calculate_need_matrix(allocation: List[List[int]], max_matrix: List[List[int]]) -> List[List[int]]:
    n = len(allocation)
    m = len(allocation[0])
    need = []
    for i in range(n):
        row = []
        for j in range(m):
            diff = max_matrix[i][j] - allocation[i][j]
            if diff < 0:
                raise ValueError(f"Allocation cannot exceed Max for process index {i}, resource index {j}")
            row.append(diff)
        need.append(row)
    return need


def solve_bankers_safety(data: BankerInput) -> SafetyResult:
    n = len(data.processes)
    m = len(data.resources)
    need = calculate_need_matrix(data.allocation, data.max_matrix)
    work = list(data.available)
    finish = [False] * n
    safe_sequence = []
    work_history = []
    explanation = [
        "Banker's Algorithm - Safety Check:",
        f"Available Resources: {dict(zip(data.resources, work))}",
        "Calculated Need Matrix (Need = Max - Allocation):"
    ]

    for i in range(n):
        explanation.append(f"  {data.processes[i]}: {need[i]}")

    count = 0
    while count < n:
        found = False
        for i in range(n):
            if not finish[i]:
                # Check if Need[i] <= Work
                can_allocate = all(need[i][j] <= work[j] for j in range(m))
                if can_allocate:
                    # Process can finish
                    before_work = list(work)
                    for j in range(m):
                        work[j] += data.allocation[i][j]
                    finish[i] = True
                    safe_sequence.append(data.processes[i])
                    found = True
                    count += 1

                    step_info = {
                        "process": data.processes[i],
                        "need": need[i],
                        "work_before": before_work,
                        "allocated_released": data.allocation[i],
                        "work_after": list(work)
                    }
                    work_history.append(step_info)
                    explanation.append(
                        f"Step {count}: Process {data.processes[i]} has Need {need[i]} <= Work {before_work}. "
                        f"It executes and releases {data.allocation[i]}. New Work = {work}."
                    )
                    break
        if not found:
            break

    is_safe = (count == n)
    if is_safe:
        explanation.append(f"System is in a SAFE STATE. Safe Sequence: {' -> '.join(safe_sequence)}.")
    else:
        deadlocked = [data.processes[i] for i in range(n) if not finish[i]]
        explanation.append(f"System is in an UNSAFE STATE (Potential Deadlock). Processes that could not complete: {deadlocked}.")

    return SafetyResult(
        is_safe=is_safe,
        safe_sequence=safe_sequence,
        need_matrix=need,
        work_history=work_history,
        explanation=explanation
    )


def solve_resource_request(data: BankerInput, req_pid: str, request_vector: List[int]) -> RequestResult:
    try:
        pid_idx = data.processes.index(req_pid)
    except ValueError:
        return RequestResult(can_grant=False, reason=f"Process {req_pid} not found in process list.", explanation=[])

    n = len(data.processes)
    m = len(data.resources)
    need = calculate_need_matrix(data.allocation, data.max_matrix)
    explanation = [f"Resource Request from {req_pid}: {dict(zip(data.resources, request_vector))}"]

    # Condition 1: Request <= Need
    for j in range(m):
        if request_vector[j] > need[pid_idx][j]:
            reason = f"Error: Process {req_pid} requested {request_vector[j]} of {data.resources[j]}, which exceeds its declared maximum need of {need[pid_idx][j]}."
            explanation.append(reason)
            return RequestResult(can_grant=False, reason=reason, explanation=explanation)

    # Condition 2: Request <= Available
    for j in range(m):
        if request_vector[j] > data.available[j]:
            reason = f"Process {req_pid} must wait because requested {request_vector[j]} of {data.resources[j]} > Available {data.available[j]}."
            explanation.append(reason)
            return RequestResult(can_grant=False, reason=reason, explanation=explanation)

    # Pretend to allocate
    new_alloc = [list(row) for row in data.allocation]
    new_avail = list(data.available)

    for j in range(m):
        new_avail[j] -= request_vector[j]
        new_alloc[pid_idx][j] += request_vector[j]

    pretend_data = BankerInput(
        processes=data.processes,
        resources=data.resources,
        allocation=new_alloc,
        max_matrix=data.max_matrix,
        available=new_avail
    )

    safety = solve_bankers_safety(pretend_data)
    if safety.is_safe:
        reason = f"Request can be GRANTED immediately. System remains in safe state with sequence: {' -> '.join(safety.safe_sequence)}."
        explanation.append(reason)
        return RequestResult(can_grant=True, reason=reason, safety_after_grant=safety, explanation=explanation)
    else:
        reason = f"Request CANNOT be granted immediately because it would leave the system in an UNSAFE state."
        explanation.append(reason)
        return RequestResult(can_grant=False, reason=reason, safety_after_grant=safety, explanation=explanation)
