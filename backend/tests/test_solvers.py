import pytest
from app.solvers.scheduling import Process, solve_fcfs, solve_srf_or_srtf, solve_round_robin
from app.solvers.page_replacement import solve_fifo, solve_lru, solve_optimal
from app.solvers.bankers import BankerInput, solve_bankers_safety, solve_resource_request

def test_srtf_pdf_question():
    procs = [
        Process(pid="P1", arrival_time=0, burst_time=6),
        Process(pid="P2", arrival_time=1, burst_time=8),
        Process(pid="P3", arrival_time=2, burst_time=7),
        Process(pid="P4", arrival_time=3, burst_time=3),
        Process(pid="P5", arrival_time=4, burst_time=4),
    ]
    result = solve_srf_or_srtf(procs, preemptive=True)
    assert result.avg_waiting_time == 7.6
    assert result.avg_turnaround_time == 13.2
    assert len(result.gantt_chart) == 5
    assert result.gantt_chart[0].pid == "P1"
    assert result.gantt_chart[1].pid == "P4"

def test_round_robin():
    procs = [
        Process(pid="P1", arrival_time=0, burst_time=5),
        Process(pid="P2", arrival_time=1, burst_time=4),
        Process(pid="P3", arrival_time=2, burst_time=2),
        Process(pid="P4", arrival_time=4, burst_time=1),
    ]
    result = solve_round_robin(procs, quantum=2)
    assert result.avg_waiting_time > 0
    assert result.context_switches > 0

def test_lru_page_replacement():
    ref_string = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
    capacity = 3
    result = solve_lru(ref_string, capacity)
    assert result.total_references == len(ref_string)
    assert result.page_faults > 0
    assert result.page_hits > 0
    assert result.page_faults + result.page_hits == len(ref_string)

def test_optimal_page_replacement():
    ref_string = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
    capacity = 3
    opt_res = solve_optimal(ref_string, capacity)
    lru_res = solve_lru(ref_string, capacity)
    # Optimal should produce <= page faults than LRU
    assert opt_res.page_faults <= lru_res.page_faults

def test_bankers_safety():
    data = BankerInput(
        processes=["P0", "P1", "P2", "P3", "P4"],
        resources=["A", "B", "C"],
        allocation=[
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ],
        max_matrix=[
            [7, 5, 3],
            [3, 2, 2],
            [9, 0, 2],
            [2, 2, 2],
            [4, 3, 3]
        ],
        available=[3, 3, 2]
    )
    result = solve_bankers_safety(data)
    assert result.is_safe is True
    assert len(result.safe_sequence) == 5
    assert result.safe_sequence[0] == "P1"

def test_bankers_resource_request():
    data = BankerInput(
        processes=["P0", "P1", "P2", "P3", "P4"],
        resources=["A", "B", "C"],
        allocation=[
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ],
        max_matrix=[
            [7, 5, 3],
            [3, 2, 2],
            [9, 0, 2],
            [2, 2, 2],
            [4, 3, 3]
        ],
        available=[3, 3, 2]
    )
    # P1 requests [1, 0, 2] -> should be granted
    req_result = solve_resource_request(data, "P1", [1, 0, 2])
    assert req_result.can_grant is True
