import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DocumentChunk(BaseModel):
    id: str
    topic: str
    subtopic: str
    source: str
    content: str
    keywords: List[str]

# Comprehensive OS course material following OSTEP and Silberschatz Operating System Concepts
COURSE_MATERIAL: List[DocumentChunk] = [
    DocumentChunk(
        id="ostep-ch2-intro",
        topic="Introduction to Operating Systems",
        subtopic="What is an Operating System?",
        source="OSTEP Chapter 2: Introduction to Operating Systems & Silberschatz Chapter 1",
        content=(
            "An Operating System (OS) is system software that acts as an intermediary between computer hardware and the user/applications. "
            "It has three primary roles:\n"
            "1. **Virtualization (The Illusionist):** Transforms physical resources (CPU, memory, disks) into powerful, easy-to-use virtual forms (processes, virtual address spaces, files).\n"
            "2. **Concurrency:** Handles multiple threads and processes running simultaneously, coordinating access to shared data to prevent race conditions.\n"
            "3. **Persistence & Resource Management (The Referee):** Manages non-volatile storage (disks, SSDs, file systems) and fairly allocates limited hardware resources (CPU time, RAM) among competing processes while enforcing security and isolation."
        ),
        keywords=["operating system", "os", "what is an operating system", "explain operating system", "introduction", "kernel", "virtualization", "concurrency", "persistence", "resource manager"]
    ),
    DocumentChunk(
        id="ostep-ch4-processes",
        topic="Process Concept",
        subtopic="Process States and PCB",
        source="OSTEP Chapter 4: Processes & Silberschatz Chapter 3",
        content=(
            "A process is an instance of a program in execution. It includes the program counter, stack, data section, "
            "and heap. The process state consists of: New, Running, Waiting (Blocked), Ready, and Terminated. "
            "A Process Control Block (PCB) contains OS information such as Process ID (PID), process state, CPU registers, "
            "memory-management information, and I/O status information."
        ),
        keywords=["pcb", "process control block", "process states", "running", "ready", "blocked", "waiting", "pid"]
    ),
    DocumentChunk(
        id="ostep-ch6-context-switch",
        topic="CPU Scheduling",
        subtopic="Context Switch Mechanism",
        source="OSTEP Chapter 6: Limited Direct Execution",
        content=(
            "A context switch is the mechanism by which the operating system saves the state of the currently executing "
            "process (saving registers to its kernel stack or PCB) and restores the state of the next process to run. "
            "Context switches are purely computational overhead because the CPU performs no productive user work during "
            "the switch. The switch is triggered by timer interrupts or system calls (traps)."
        ),
        keywords=["context switch", "timer interrupt", "overhead", "pcb", "registers", "trap", "kernel stack"]
    ),
    DocumentChunk(
        id="ostep-ch7-scheduling",
        topic="CPU Scheduling",
        subtopic="Preemptive vs Non-Preemptive Scheduling",
        source="OSTEP Chapter 7: Scheduling Introduction",
        content=(
            "Scheduling algorithms determine the order of CPU execution among ready processes. "
            "Non-preemptive algorithms (FCFS, SJF) allow a process to run until it terminates or blocks for I/O. "
            "Preemptive algorithms (SRTF, Round Robin) can interrupt an actively executing process when a higher-priority "
            "process arrives or when the time quantum expires. Metrics include Turnaround Time (Completion - Arrival) "
            "and Waiting Time (Turnaround - Burst)."
        ),
        keywords=["fcfs", "sjf", "srtf", "round robin", "turnaround time", "waiting time", "preemption", "gantt chart"]
    ),
    DocumentChunk(
        id="cpu-scheduling-starvation",
        topic="CPU Scheduling & Process Synchronization",
        subtopic="Starvation (Indefinite Blocking) and The Aging Solution",
        source="Silberschatz Chapter 5: CPU Scheduling (Section 5.3.3) & OSTEP Chapter 7",
        content=(
            "**Starvation (also called Indefinite Blocking)** is a condition in CPU scheduling and resource allocation where a process is ready to execute, but is perpetually denied CPU time or necessary resources because higher-priority or shorter processes continuously arrive.\n\n"
            "### 1. Why Starvation Occurs\n"
            "- **Priority Scheduling:** A major problem with priority scheduling algorithms is that a steady stream of higher-priority processes can prevent a low-priority process from ever obtaining the CPU.\n"
            "- **Shortest Job First (SJF / SRTF):** Long processes may starve if short processes keep arriving continuously.\n"
            "- **Unfair Locks / Semaphores:** Weak semaphores that don't enforce FIFO queuing can allow certain threads to be repeatedly bypassed.\n\n"
            "### 2. How the Operating System Solves It: Aging\n"
            "The primary solution to starvation in operating systems is **Aging**:\n"
            "- **Aging Mechanism:** The operating system gradually increases the priority of processes that wait in the system for a long time.\n"
            "- *Example:* If priority ranges from 0 (lowest) to 127 (highest), the OS might increase the priority of a waiting process by 1 every 15 minutes. Eventually, even a low-priority process will reach the highest priority and run to completion.\n\n"
            "### 3. Starvation vs. Deadlock (Key Exam Distinction)\n"
            "- **Deadlock:** Two or more processes are permanently blocked because each holds a resource the other needs. **No process makes progress**.\n"
            "- **Starvation:** The CPU and system are actively running and doing work, but **one or more unlucky low-priority processes are starved of attention**."
        ),
        keywords=["starvation", "what is starvation", "indefinite blocking", "aging", "aging technique", "priority scheduling starvation", "starvation vs deadlock"]
    ),
    DocumentChunk(
        id="concurrency-mutual-exclusion",
        topic="Process Synchronization",
        subtopic="Mutual Exclusion & The Critical Section Problem",
        source="Silberschatz Chapter 6: Synchronization Tools & OSTEP Chapter 28: Locks",
        content=(
            "**Mutual Exclusion** is a fundamental concurrency principle which dictates that when one process is executing inside its **Critical Section** (accessing shared memory, files, or variables), no other process is allowed to execute inside that critical section simultaneously.\n\n"
            "### Why is it needed?\n"
            "Without mutual exclusion, concurrent access leads to **Race Conditions**, where the final outcome depends unpredictably on the relative scheduling order, corrupting data integrity.\n\n"
            "### Requirements for a Valid Solution:\n"
            "1. **Mutual Exclusion:** No two processes may be simultaneously present in their critical sections.\n"
            "2. **Progress:** If no process is executing in its critical section and some wish to enter, only those not in their remainder sections can participate in deciding who enters next, without indefinite postponement.\n"
            "3. **Bounded Waiting:** A bound must exist on the number of times other processes are allowed to enter their critical sections after a process has made a request to enter.\n\n"
            "### Mechanisms to Enforce Mutual Exclusion:\n"
            "- **Software Solutions:** Peterson's Algorithm (for 2 processes), Lamport's Bakery Algorithm (for N processes).\n"
            "- **Hardware Primitives:** Atomic instructions like `TestAndSet()`, `CompareAndSwap()` (CAS).\n"
            "- **OS Primitives:** Mutex Locks, Binary/Counting Semaphores, Monitors.\n\n"
            "### Relation to Deadlocks:\n"
            "Mutual exclusion is also the **first of the four Coffman conditions** required for a deadlock to exist."
        ),
        keywords=["mutual exclusion", "critical section", "critical section problem", "what is mutual exclusion", "race condition", "mutual exclusion problem"]
    ),
    DocumentChunk(
        id="peterson-algorithm",
        topic="Synchronization",
        subtopic="Peterson's Algorithm",
        source="Silberschatz Chapter 6: Synchronization Tools & OSTEP Chapter 28",
        content=(
            "Peterson's Algorithm is a classic software-based solution to the critical-section problem for two processes (P0 and P1). "
            "It uses two shared variables:\n"
            "- `boolean flag[2]`: `flag[i] = true` indicates process `i` is ready to enter its critical section.\n"
            "- `int turn`: indicates whose turn it is to enter the critical section.\n"
            "Process `i` sets `flag[i] = true` and `turn = j`. It then waits in a while loop `while (flag[j] && turn == j);` before entering. "
            "Peterson's algorithm provably guarantees all three critical section criteria: **Mutual Exclusion**, **Progress**, and **Bounded Waiting**."
        ),
        keywords=["peterson", "peterson's algorithm", "petersons algorithm", "peterson algorithm", "flag", "turn", "critical section", "two processes"]
    ),
    DocumentChunk(
        id="bakery-algorithm",
        topic="Synchronization",
        subtopic="Lamport's Bakery Algorithm",
        source="Silberschatz Chapter 6: Synchronization Tools",
        content=(
            "Lamport's Bakery Algorithm is a classic mutual exclusion algorithm for N competing processes, based on how customers take "
            "numbered tickets in a bakery.\n"
            "- Each process receives a numbered ticket upon entering the customer queue (`ticket = 1 + max(all tickets)`).\n"
            "- The process with the lowest ticket number is served first. If two processes receive the same number, the process with the smaller PID gets priority (`(ticket[i], i) < (ticket[j], j)`).\n"
            "It guarantees **Mutual Exclusion**, **Progress**, and **Bounded Waiting (First-Come, First-Served)** for any arbitrary number of $N$ processes without specialized hardware atomic instructions."
        ),
        keywords=["bakery", "bakery algorithm", "lamport", "lamport's bakery", "ticket", "n processes", "critical section", "mutual exclusion"]
    ),
    DocumentChunk(
        id="ostep-ch28-locks",
        topic="Concurrency",
        subtopic="Race Conditions and Critical Section",
        source="OSTEP Chapter 28: Locks & Synchronization",
        content=(
            "A race condition occurs when multiple threads or processes access shared data concurrently and the outcome "
            "depends on the order of execution. The critical section is the portion of code where shared resources are accessed. "
            "Any valid synchronization solution must satisfy three requirements:\n"
            "1. **Mutual Exclusion:** At most one process in the critical section at a time.\n"
            "2. **Progress:** If no process is in the critical section, only processes wishing to enter can participate in the decision.\n"
            "3. **Bounded Waiting:** A bound must exist on the number of times other processes can enter before a requesting process is granted entry."
        ),
        keywords=["race condition", "critical section", "mutual exclusion", "progress", "bounded waiting", "locks", "threads"]
    ),
    DocumentChunk(
        id="ostep-ch31-semaphores",
        topic="Concurrency",
        subtopic="Semaphores and Classical Synchronization",
        source="OSTEP Chapter 31: Semaphores",
        content=(
            "A semaphore is an integer synchronization variable accessed only via two atomic operations: `wait()` (P/down) and `signal()` (V/up). "
            "A binary semaphore acts as a mutex. A counting semaphore manages a pool of finite resources. "
            "Classical problems include:\n"
            "- **Producer-Consumer (Bounded Buffer):** Uses empty, full, and mutex semaphores.\n"
            "- **Readers-Writers:** Allows concurrent readers, but gives writers exclusive access.\n"
            "- **Dining Philosophers:** Illustrates deadlocks and starvation when acquiring multiple shared forks."
        ),
        keywords=["semaphore", "mutex", "wait", "signal", "p", "v", "counting semaphore", "producer consumer", "dining philosophers", "readers writers"]
    ),
    DocumentChunk(
        id="ostep-ch32-deadlocks",
        topic="Deadlocks",
        subtopic="Coffman Conditions and Banker's Algorithm",
        source="OSTEP Chapter 32: Common Concurrency Problems & Silberschatz Chapter 7",
        content=(
            "A deadlock is a situation where every process in a set is waiting for an event that only another process in the set "
            "can cause. Deadlock requires four Coffman conditions simultaneously:\n"
            "1. **Mutual Exclusion:** Non-shareable resource mode.\n"
            "2. **Hold and Wait:** A process holds at least one resource while waiting for another.\n"
            "3. **No Preemption:** Resources cannot be forcibly preempted from a process.\n"
            "4. **Circular Wait:** A closed chain of processes exists where each process holds a resource needed by the next.\n"
            "Dijkstra's Banker's Algorithm avoids deadlocks by ensuring the system never enters an unsafe state via safety and resource-request calculations."
        ),
        keywords=["deadlock", "coffman", "coffman conditions", "circular wait", "hold and wait", "no preemption", "banker", "banker's algorithm", "safe state", "safe sequence"]
    ),
    DocumentChunk(
        id="memory-segmentation",
        topic="Main Memory Management",
        subtopic="Segmentation & Address Translation",
        source="Silberschatz Chapter 7: Main Memory (Section 7.6) & OSTEP Chapter 16: Segmentation",
        content=(
            "**Segmentation** is a memory-management scheme that reflects the programmer's view of memory. "
            "Instead of viewing physical memory as a linear array of bytes or fixed-size pages, a program is divided into logical variable-length segments corresponding to program components:\n"
            "- Code / Text Segment\n"
            "- Stack Segment\n"
            "- Heap Segment\n"
            "- Global / Data Segment\n"
            "- Symbol Table\n\n"
            "### 1. Logical Address Structure\n"
            "A logical address in segmentation is a two-tuple: **`<segment-number (s), offset (d)>`**.\n\n"
            "### 2. Segment Table & Hardware Translation\n"
            "The CPU uses a **Segment Table** where each entry contains two critical registers:\n"
            "- **Base:** The physical starting address where the segment resides in main memory.\n"
            "- **Limit:** The length/size of the segment.\n\n"
            "**Translation Rule:**\n"
            "1. When the CPU generates `<s, d>`, the hardware checks: is `d < limit`?\n"
            "2. If `d >= limit`, the hardware generates a trap: **Segmentation Fault** (illegal memory access).\n"
            "3. If `d < limit`, Physical Address = **`base + d`**.\n\n"
            "### 3. Paging vs. Segmentation (Key Differences)\n"
            "- **Block Size:** Paging has fixed-size blocks (pages/frames); Segmentation has variable-length blocks.\n"
            "- **Programmer View:** Paging is invisible to the programmer (hardware/OS managed); Segmentation explicitly mirrors programmer logical modularity.\n"
            "- **Fragmentation:** Paging suffers from **Internal Fragmentation** (unused space inside the last page), but eliminates external fragmentation. Segmentation suffers from **External Fragmentation** (variable holes between allocated segments requiring compaction), but eliminates internal fragmentation."
        ),
        keywords=["segmentation", "segment", "segment table", "base and limit", "segmentation fault", "paging vs segmentation", "what is segmentation", "logical address"]
    ),
    DocumentChunk(
        id="ostep-ch18-paging",
        topic="Virtual Memory",
        subtopic="Paging, TLB, and Address Translation",
        source="OSTEP Chapter 18: Paging & Chapter 19: TLBs",
        content=(
            "Paging is a memory-management scheme where physical memory is divided into fixed-size frames and logical memory "
            "into pages of equal size. An address generated by the CPU has two parts: Page Number (p) and Offset (d). "
            "The Page Table maps page numbers to physical frame numbers. The TLB (Translation Lookaside Buffer) is a fast hardware "
            "cache for page translations. Effective Access Time (EAT) = (Hit_Ratio * (TLB_time + Memory_time)) + ((1 - Hit_Ratio) * (TLB_time + 2 * Memory_time))."
        ),
        keywords=["paging", "page table", "frame", "offset", "tlb", "translation lookaside buffer", "eat", "effective access time"]
    ),
    DocumentChunk(
        id="ostep-ch22-page-replacement",
        topic="Virtual Memory",
        subtopic="Page Replacement and Belady's Anomaly",
        source="OSTEP Chapter 22: Beyond Physical Memory - Policies",
        content=(
            "When a page fault occurs and no free memory frames exist, a page replacement policy chooses which page to evict. "
            "Common policies include:\n"
            "- **FIFO:** Replaces the oldest loaded page. Suffers from Belady's Anomaly (increasing frame allocation can lead to more page faults).\n"
            "- **Optimal (OPT/MIN):** Replaces the page not used for the longest future time. Minimizes page faults.\n"
            "- **LRU:** Replaces the page not used for the longest past time. Immune to Belady's Anomaly (stack algorithm).\n"
            "- **Clock:** Second-chance algorithm using a circular pointer and reference bit."
        ),
        keywords=["page replacement", "fifo", "lru", "optimal", "clock", "second chance", "belady's anomaly", "page fault", "thrashing"]
    ),
    DocumentChunk(
        id="disk-scheduling",
        topic="Storage Systems",
        subtopic="Disk Scheduling Algorithms",
        source="Silberschatz Chapter 10: Mass-Storage Structure",
        content=(
            "Disk scheduling algorithms minimize disk arm seek time and head movement when servicing disk I/O requests:\n"
            "- **FCFS:** First-Come, First-Served.\n"
            "- **SSTF (Shortest Seek Time First):** Selects the request with minimum seek distance from current head position; may cause starvation.\n"
            "- **SCAN (Elevator Algorithm):** The arm moves toward one end servicing requests until reaching the end, then reverses direction.\n"
            "- **C-SCAN (Circular SCAN):** Moves in one direction servicing requests; upon reaching the end, returns to the start without servicing on return.\n"
            "- **LOOK & C-LOOK:** Like SCAN/C-SCAN, but only goes as far as the final request in each direction, avoiding travel to the physical disk edge."
        ),
        keywords=["disk scheduling", "sstf", "scan", "c-scan", "look", "c-look", "seek time", "head movement", "elevator"]
    ),
    DocumentChunk(
        id="linux-zombie-orphan",
        topic="Process Management",
        subtopic="Zombie and Orphan Processes in Linux",
        source="Linux Manual Pages (man 2 waitpid, man 2 fork)",
        content=(
            "A zombie process (state Z in ps/top) is a process that has completed execution via exit(), but whose parent has "
            "not yet called wait() or waitpid() to read its termination exit status. The zombie retains an entry in the OS process table.\n"
            "An orphan process is a process whose parent has terminated while the child is still executing. In Linux, orphan "
            "processes are immediately reparented to process ID 1 (systemd or init), which regularly calls wait() to reap them."
        ),
        keywords=["zombie", "orphan", "wait", "waitpid", "exit", "reparent", "init", "systemd", "ps", "state z"]
    )
]
