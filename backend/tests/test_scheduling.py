import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.solvers.scheduling import Process, solve_srf_or_srtf, solve_fcfs, solve_round_robin

def test_pdf_srtf_example():
    """
    PDF Question:
    P1 to P5 arrive at 0, 1, 2, 3, 4 with burst times 6, 8, 7, 3, 4.
    Algorithm: SRTF
    """
    procs = [
        Process(pid="P1", arrival_time=0, burst_time=6),
        Process(pid="P2", arrival_time=1, burst_time=8),
        Process(pid="P3", arrival_time=2, burst_time=7),
        Process(pid="P4", arrival_time=3, burst_time=3),
        Process(pid="P5", arrival_time=4, burst_time=4),
    ]

    result = solve_srf_or_srtf(procs, preemptive=True)
    print("=== SRTF RESULT FROM PDF EXAMPLE ===")
    print(f"Algorithm: {result.algorithm}")
    print("\nGantt Chart:")
    for b in result.gantt_chart:
        print(f"  [{b.start} -> {b.end}] : {b.pid}")

    print("\nProcess Metrics:")
    for m in result.process_metrics:
        print(f"  {m.pid}: AT={m.arrival_time}, BT={m.burst_time}, CT={m.completion_time}, TAT={m.turnaround_time}, WT={m.waiting_time}, RT={m.response_time}")

    print(f"\nAverage Turnaround Time: {result.avg_turnaround_time}")
    print(f"Average Waiting Time: {result.avg_waiting_time}")
    print(f"Context Switches: {result.context_switches}")
    print("\nStep-by-step trace:")
    for step in result.step_by_step_explanation:
        print(f"  - {step}")

    # Sanity checks
    assert len(result.gantt_chart) > 0
    assert result.avg_waiting_time > 0
    print("\n✅ TEST PASSED!")

if __name__ == "__main__":
    test_pdf_srtf_example()
