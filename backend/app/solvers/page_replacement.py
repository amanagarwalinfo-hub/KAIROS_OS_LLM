from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PageStep(BaseModel):
    step: int
    page: int
    is_fault: bool
    frames: List[Optional[int]]  # Frame contents at this step, None for empty frame
    evicted_page: Optional[int] = None
    reason: str

class PageReplacementResult(BaseModel):
    algorithm: str
    capacity: int
    reference_string: List[int]
    steps: List[PageStep]
    total_references: int
    page_faults: int
    page_hits: int
    fault_ratio: float
    hit_ratio: float
    step_by_step_explanation: List[str]


def solve_fifo(reference_string: List[int], capacity: int) -> PageReplacementResult:
    if capacity <= 0:
        raise ValueError("Capacity must be greater than 0.")

    frames: List[Optional[int]] = [None] * capacity
    queue: List[int] = []  # Tracks FIFO order of pages in frames
    steps: List[PageStep] = []
    explanations: List[str] = [
        f"FIFO (First-In, First-Out) Page Replacement with frame capacity = {capacity}.",
        "Replaces the page that has been in memory the longest when a page fault occurs."
    ]
    faults = 0
    hits = 0

    for idx, page in enumerate(reference_string):
        if page in frames:
            hits += 1
            reason = f"Page {page} is already in frame. (HIT)"
            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=False,
                frames=list(frames),
                evicted_page=None,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): HIT. Frames: {list(frames)}")
        else:
            faults += 1
            evicted = None
            if None in frames:
                # Empty slot available
                slot = frames.index(None)
                frames[slot] = page
                queue.append(page)
                reason = f"Page {page} brought into empty frame {slot}. (FAULT)"
            else:
                # Evict oldest in queue
                evicted = queue.pop(0)
                slot = frames.index(evicted)
                frames[slot] = page
                queue.append(page)
                reason = f"Frame full. Oldest page {evicted} is evicted and replaced by page {page}. (FAULT)"

            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=True,
                frames=list(frames),
                evicted_page=evicted,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): FAULT. {reason} Frames: {list(frames)}")

    total = len(reference_string)
    hit_ratio = round(hits / total, 4) if total > 0 else 0.0
    fault_ratio = round(faults / total, 4) if total > 0 else 0.0

    explanations.append(f"Summary: Total References = {total}, Faults = {faults}, Hits = {hits}, Hit Ratio = {hit_ratio * 100}%, Fault Ratio = {fault_ratio * 100}%.")

    return PageReplacementResult(
        algorithm="FIFO",
        capacity=capacity,
        reference_string=reference_string,
        steps=steps,
        total_references=total,
        page_faults=faults,
        page_hits=hits,
        fault_ratio=fault_ratio,
        hit_ratio=hit_ratio,
        step_by_step_explanation=explanations
    )


def solve_lru(reference_string: List[int], capacity: int) -> PageReplacementResult:
    if capacity <= 0:
        raise ValueError("Capacity must be greater than 0.")

    frames: List[Optional[int]] = [None] * capacity
    last_used: Dict[int, int] = {}  # Page -> last access index
    steps: List[PageStep] = []
    explanations: List[str] = [
        f"LRU (Least Recently Used) Page Replacement with frame capacity = {capacity}.",
        "Replaces the page that has not been used for the longest period of time."
    ]
    faults = 0
    hits = 0

    for idx, page in enumerate(reference_string):
        last_used[page] = idx
        if page in frames:
            hits += 1
            reason = f"Page {page} is already in frame. Last access updated to step {idx + 1}. (HIT)"
            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=False,
                frames=list(frames),
                evicted_page=None,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): HIT. Frames: {list(frames)}")
        else:
            faults += 1
            evicted = None
            if None in frames:
                slot = frames.index(None)
                frames[slot] = page
                reason = f"Page {page} brought into empty frame {slot}. (FAULT)"
            else:
                # Find page currently in frames with minimum last_used timestamp
                evicted = min(frames, key=lambda p: last_used.get(p, -1))
                slot = frames.index(evicted)
                frames[slot] = page
                reason = f"Frame full. Page {evicted} was least recently used (last accessed at step {last_used[evicted] + 1}) and is evicted for page {page}. (FAULT)"

            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=True,
                frames=list(frames),
                evicted_page=evicted,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): FAULT. {reason} Frames: {list(frames)}")

    total = len(reference_string)
    hit_ratio = round(hits / total, 4) if total > 0 else 0.0
    fault_ratio = round(faults / total, 4) if total > 0 else 0.0

    explanations.append(f"Summary: Total References = {total}, Faults = {faults}, Hits = {hits}, Hit Ratio = {hit_ratio * 100}%, Fault Ratio = {fault_ratio * 100}%.")

    return PageReplacementResult(
        algorithm="LRU",
        capacity=capacity,
        reference_string=reference_string,
        steps=steps,
        total_references=total,
        page_faults=faults,
        page_hits=hits,
        fault_ratio=fault_ratio,
        hit_ratio=hit_ratio,
        step_by_step_explanation=explanations
    )


def solve_optimal(reference_string: List[int], capacity: int) -> PageReplacementResult:
    if capacity <= 0:
        raise ValueError("Capacity must be greater than 0.")

    frames: List[Optional[int]] = [None] * capacity
    steps: List[PageStep] = []
    explanations: List[str] = [
        f"Optimal (OPT / MIN) Page Replacement with frame capacity = {capacity}.",
        "Replaces the page that will not be used for the longest period of time in the future."
    ]
    faults = 0
    hits = 0
    total = len(reference_string)

    for idx, page in enumerate(reference_string):
        if page in frames:
            hits += 1
            reason = f"Page {page} is already in frame. (HIT)"
            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=False,
                frames=list(frames),
                evicted_page=None,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): HIT. Frames: {list(frames)}")
        else:
            faults += 1
            evicted = None
            if None in frames:
                slot = frames.index(None)
                frames[slot] = page
                reason = f"Page {page} loaded into empty frame {slot}. (FAULT)"
            else:
                # For each resident page, find next occurrence index in reference_string after idx
                future_occurrences = {}
                for p in frames:
                    try:
                        next_idx = reference_string.index(p, idx + 1)
                        future_occurrences[p] = next_idx
                    except ValueError:
                        future_occurrences[p] = float('inf')  # Never used again

                # Evict page with max next occurrence (furthest in future or never used)
                evicted = max(frames, key=lambda p: future_occurrences[p])
                slot = frames.index(evicted)
                frames[slot] = page

                if future_occurrences[evicted] == float('inf'):
                    detail = f"Page {evicted} will never be referenced again"
                else:
                    detail = f"Page {evicted} will not be used until step {future_occurrences[evicted] + 1} (longest future distance)"

                reason = f"Frame full. {detail}, so it is evicted and replaced by page {page}. (FAULT)"

            steps.append(PageStep(
                step=idx + 1,
                page=page,
                is_fault=True,
                frames=list(frames),
                evicted_page=evicted,
                reason=reason
            ))
            explanations.append(f"Step {idx + 1} (Ref {page}): FAULT. {reason} Frames: {list(frames)}")

    hit_ratio = round(hits / total, 4) if total > 0 else 0.0
    fault_ratio = round(faults / total, 4) if total > 0 else 0.0

    explanations.append(f"Summary: Total References = {total}, Faults = {faults}, Hits = {hits}, Hit Ratio = {hit_ratio * 100}%, Fault Ratio = {fault_ratio * 100}%.")

    return PageReplacementResult(
        algorithm="Optimal",
        capacity=capacity,
        reference_string=reference_string,
        steps=steps,
        total_references=total,
        page_faults=faults,
        page_hits=hits,
        fault_ratio=fault_ratio,
        hit_ratio=hit_ratio,
        step_by_step_explanation=explanations
    )
