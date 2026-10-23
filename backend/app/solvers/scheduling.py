from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Process(BaseModel):
    pid: str
    arrival_time: int = Field(ge=0)
    burst_time: int = Field(gt=0)
    priority: Optional[int] = 0  # Lower number = higher priority convention (or configurable)

class GanttBlock(BaseModel):
    pid: str  # Can be "IDLE" if no process is ready
    start: int
    end: int

class ProcessMetrics(BaseModel):
    pid: str
    arrival_time: int
    burst_time: int
    completion_time: int
    turnaround_time: int
    waiting_time: int
    response_time: int

class SchedulingResult(BaseModel):
    algorithm: str
    gantt_chart: List[GanttBlock]
    process_metrics: List[ProcessMetrics]
    avg_turnaround_time: float
    avg_waiting_time: float
    avg_response_time: float
    context_switches: int
    step_by_step_explanation: List[str]


def solve_fcfs(processes: List[Process]) -> SchedulingResult:
    # Sort primarily by arrival time
    procs = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    current_time = 0
    gantt: List[GanttBlock] = []
    metrics: List[ProcessMetrics] = []
    explanations: List[str] = []
    context_switches = 0
    last_pid = None

    explanations.append("First-Come, First-Served (FCFS) is a non-preemptive scheduling algorithm.")
    explanations.append("Processes are scheduled in strict order of their arrival times.")

    for p in procs:
        if current_time < p.arrival_time:
            explanations.append(f"At t={current_time}: CPU is idle until t={p.arrival_time} when {p.pid} arrives.")
            gantt.append(GanttBlock(pid="IDLE", start=current_time, end=p.arrival_time))
            current_time = p.arrival_time
            last_pid = "IDLE"

        start_time = current_time
        if last_pid is not None and last_pid != p.pid and last_pid != "IDLE":
            context_switches += 1
        
        last_pid = p.pid
        response_time = start_time - p.arrival_time
        current_time += p.burst_time
        completion_time = current_time
        turnaround_time = completion_time - p.arrival_time
        waiting_time = turnaround_time - p.burst_time

        gantt.append(GanttBlock(pid=p.pid, start=start_time, end=completion_time))
        explanations.append(
            f"At t={start_time}: Process {p.pid} runs for {p.burst_time} units until t={completion_time}. "
            f"Completion Time (CT) = {completion_time}, Turnaround Time (TAT) = {turnaround_time}, Waiting Time (WT) = {waiting_time}."
        )

        metrics.append(ProcessMetrics(
            pid=p.pid,
            arrival_time=p.arrival_time,
            burst_time=p.burst_time,
            completion_time=completion_time,
            turnaround_time=turnaround_time,
            waiting_time=waiting_time,
            response_time=response_time
        ))

    # Sort metrics by original process order or pid
    metrics_sorted = sorted(metrics, key=lambda m: m.pid)
    n = len(procs)
    avg_tat = round(sum(m.turnaround_time for m in metrics) / n, 2)
    avg_wt = round(sum(m.waiting_time for m in metrics) / n, 2)
    avg_rt = round(sum(m.response_time for m in metrics) / n, 2)

    explanations.append(f"Summary: Average Turnaround Time = {avg_tat}, Average Waiting Time = {avg_wt}, Average Response Time = {avg_rt}.")

    return SchedulingResult(
        algorithm="FCFS",
        gantt_chart=gantt,
        process_metrics=metrics_sorted,
        avg_turnaround_time=avg_tat,
        avg_waiting_time=avg_wt,
        avg_response_time=avg_rt,
        context_switches=context_switches,
        step_by_step_explanation=explanations
    )


def solve_srf_or_srtf(processes: List[Process], preemptive: bool = True) -> SchedulingResult:
    """
    Solves SJF (preemptive=False) or SRTF (preemptive=True).
    Tie-breaking: earlier arrival time, then alphabetical PID.
    """
    algo_name = "SRTF (Preemptive SJF)" if preemptive else "SJF (Non-preemptive)"
    n = len(processes)
    if n == 0:
        raise ValueError("Process list cannot be empty.")

    rem_burst = {p.pid: p.burst_time for p in processes}
    proc_map = {p.pid: p for p in processes}
    first_response = {}
    completion_times = {}

    current_time = 0
    completed = 0
    current_running: Optional[str] = None
    gantt: List[GanttBlock] = []
    explanations: List[str] = [
        f"{algo_name} prioritizes processes with the shortest {'remaining ' if preemptive else ''}burst time."
    ]
    context_switches = 0

    # Total remaining work tracking
    while completed < n:
        # Ready processes at current_time
        ready = [p for p in processes if p.arrival_time <= current_time and rem_burst[p.pid] > 0]

        if not ready:
            # Advance to next arrival
            future_arrivals = [p.arrival_time for p in processes if p.arrival_time > current_time and rem_burst[p.pid] > 0]
            next_arrival = min(future_arrivals)
            explanations.append(f"At t={current_time}: CPU is idle until t={next_arrival}.")
            if gantt and gantt[-1].pid == "IDLE":
                gantt[-1].end = next_arrival
            else:
                gantt.append(GanttBlock(pid="IDLE", start=current_time, end=next_arrival))
            current_time = next_arrival
            current_running = None
            continue

        # Select process: min remaining burst, then min arrival time, then pid
        best_proc = min(ready, key=lambda p: (rem_burst[p.pid], p.arrival_time, p.pid))
        chosen_pid = best_proc.pid

        # Check for context switch
        if current_running is not None and current_running != chosen_pid:
            context_switches += 1
            if preemptive and rem_burst.get(current_running, 0) > 0:
                explanations.append(
                    f"At t={current_time}: Process {current_running} is PREEMPTED by {chosen_pid} "
                    f"because {chosen_pid} has shorter remaining burst ({rem_burst[chosen_pid]} < {rem_burst[current_running]})."
                )
            elif rem_burst.get(current_running, 0) == 0:
                explanations.append(
                    f"At t={current_time}: Process {current_running} finished. CPU switches to {chosen_pid} (remaining burst = {rem_burst[chosen_pid]})."
                )

        if chosen_pid not in first_response:
            first_response[chosen_pid] = current_time

        current_running = chosen_pid

        if preemptive:
            # Run for 1 time unit or until next event (arrival or completion)
            next_arrivals = [p.arrival_time for p in processes if p.arrival_time > current_time and rem_burst[p.pid] > 0]
            time_to_completion = rem_burst[chosen_pid]
            if next_arrivals:
                step = min(min(next_arrivals) - current_time, time_to_completion)
            else:
                step = time_to_completion

            step = max(1, step)
            rem_burst[chosen_pid] -= step
            block_start = current_time
            current_time += step
            block_end = current_time

            # Record in Gantt
            if gantt and gantt[-1].pid == chosen_pid:
                gantt[-1].end = block_end
            else:
                gantt.append(GanttBlock(pid=chosen_pid, start=block_start, end=block_end))

            if rem_burst[chosen_pid] == 0:
                completed += 1
                completion_times[chosen_pid] = current_time
                tat = current_time - proc_map[chosen_pid].arrival_time
                wt = tat - proc_map[chosen_pid].burst_time
                explanations.append(
                    f"At t={current_time}: {chosen_pid} completes. CT={current_time}, TAT={tat}, WT={wt}."
                )
        else:
            # Non-preemptive runs to completion
            run_duration = rem_burst[chosen_pid]
            block_start = current_time
            current_time += run_duration
            rem_burst[chosen_pid] = 0
            completed += 1
            completion_times[chosen_pid] = current_time
            gantt.append(GanttBlock(pid=chosen_pid, start=block_start, end=current_time))
            tat = current_time - proc_map[chosen_pid].arrival_time
            wt = tat - proc_map[chosen_pid].burst_time
            explanations.append(
                f"At t={block_start}: {chosen_pid} runs non-preemptively until completion at t={current_time}. CT={current_time}, TAT={tat}, WT={wt}."
            )

    metrics: List[ProcessMetrics] = []
    for p in processes:
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        rt = first_response[p.pid] - p.arrival_time
        metrics.append(ProcessMetrics(
            pid=p.pid,
            arrival_time=p.arrival_time,
            burst_time=p.burst_time,
            completion_time=ct,
            turnaround_time=tat,
            waiting_time=wt,
            response_time=rt
        ))

    metrics_sorted = sorted(metrics, key=lambda m: m.pid)
    avg_tat = round(sum(m.turnaround_time for m in metrics) / n, 2)
    avg_wt = round(sum(m.waiting_time for m in metrics) / n, 2)
    avg_rt = round(sum(m.response_time for m in metrics) / n, 2)

    explanations.append(f"Summary: Average Turnaround Time = {avg_tat}, Average Waiting Time = {avg_wt}, Average Response Time = {avg_rt}.")

    return SchedulingResult(
        algorithm=algo_name,
        gantt_chart=gantt,
        process_metrics=metrics_sorted,
        avg_turnaround_time=avg_tat,
        avg_waiting_time=avg_wt,
        avg_response_time=avg_rt,
        context_switches=context_switches,
        step_by_step_explanation=explanations
    )


def solve_round_robin(processes: List[Process], quantum: int) -> SchedulingResult:
    """
    Solves Round Robin (RR) with a given time quantum.
    """
    if quantum <= 0:
        raise ValueError("Quantum must be greater than 0.")
    n = len(processes)
    if n == 0:
        raise ValueError("Process list cannot be empty.")

    rem_burst = {p.pid: p.burst_time for p in processes}
    proc_map = {p.pid: p for p in processes}
    first_response = {}
    completion_times = {}

    current_time = 0
    completed = 0
    gantt: List[GanttBlock] = []
    explanations: List[str] = [
        f"Round Robin Scheduling with Time Quantum = {quantum}.",
        "Ready queue maintains processes in FIFO order. If a process does not finish within its quantum, it is preempted to the back of the queue."
    ]
    context_switches = 0

    ready_queue: List[str] = []
    visited_arrivals = set()

    # Helper to check new arrivals up to current_time
    def check_arrivals():
        arrivals = [p for p in processes if p.arrival_time <= current_time and p.pid not in visited_arrivals]
        # Sort arrivals by arrival_time, then pid
        arrivals.sort(key=lambda p: (p.arrival_time, p.pid))
        for p in arrivals:
            ready_queue.append(p.pid)
            visited_arrivals.add(p.pid)

    check_arrivals()
    last_pid = None

    while completed < n:
        if not ready_queue:
            # CPU is idle
            unvisited = [p for p in processes if p.pid not in visited_arrivals]
            if unvisited:
                next_arrival = min(p.arrival_time for p in unvisited)
                explanations.append(f"At t={current_time}: CPU is idle until t={next_arrival}.")
                gantt.append(GanttBlock(pid="IDLE", start=current_time, end=next_arrival))
                current_time = next_arrival
                check_arrivals()
                last_pid = "IDLE"
                continue

        chosen_pid = ready_queue.pop(0)

        if last_pid is not None and last_pid != chosen_pid and last_pid != "IDLE":
            context_switches += 1
        last_pid = chosen_pid

        if chosen_pid not in first_response:
            first_response[chosen_pid] = current_time

        execute_time = min(quantum, rem_burst[chosen_pid])
        start_time = current_time
        current_time += execute_time
        rem_burst[chosen_pid] -= execute_time

        gantt.append(GanttBlock(pid=chosen_pid, start=start_time, end=current_time))

        # Check for processes arriving during this slice BEFORE requeueing current process
        check_arrivals()

        if rem_burst[chosen_pid] == 0:
            completed += 1
            completion_times[chosen_pid] = current_time
            tat = current_time - proc_map[chosen_pid].arrival_time
            wt = tat - proc_map[chosen_pid].burst_time
            explanations.append(
                f"At t={start_time}: {chosen_pid} runs for {execute_time} units and FINISHES at t={current_time}. CT={current_time}, TAT={tat}, WT={wt}."
            )
        else:
            ready_queue.append(chosen_pid)
            explanations.append(
                f"At t={start_time}: {chosen_pid} runs for {execute_time} units (remaining burst = {rem_burst[chosen_pid]}). Preempted back to queue at t={current_time}."
            )

    metrics: List[ProcessMetrics] = []
    for p in processes:
        ct = completion_times[p.pid]
        tat = ct - p.arrival_time
        wt = tat - p.burst_time
        rt = first_response[p.pid] - p.arrival_time
        metrics.append(ProcessMetrics(
            pid=p.pid,
            arrival_time=p.arrival_time,
            burst_time=p.burst_time,
            completion_time=ct,
            turnaround_time=tat,
            waiting_time=wt,
            response_time=rt
        ))

    metrics_sorted = sorted(metrics, key=lambda m: m.pid)
    avg_tat = round(sum(m.turnaround_time for m in metrics) / n, 2)
    avg_wt = round(sum(m.waiting_time for m in metrics) / n, 2)
    avg_rt = round(sum(m.response_time for m in metrics) / n, 2)

    explanations.append(f"Summary: Average Turnaround Time = {avg_tat}, Average Waiting Time = {avg_wt}, Average Response Time = {avg_rt}.")

    return SchedulingResult(
        algorithm=f"Round Robin (Quantum={quantum})",
        gantt_chart=gantt,
        process_metrics=metrics_sorted,
        avg_turnaround_time=avg_tat,
        avg_waiting_time=avg_wt,
        avg_response_time=avg_rt,
        context_switches=context_switches,
        step_by_step_explanation=explanations
    )
