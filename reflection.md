# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Initial UML: a small set of core classes centered on scheduling flow: `Scheduler` orchestrates, `Task` represents a care activity, and `PetOwner`/`Pet` hold profile data used by the planner. I modeled the flow as: create task → enrich with pet/owner info → generate/display plan.
- Classes and responsibilities:
    - `Task`: store task details (type, time window, duration, priority).
    - `Pet`: store pet info (species, needs, preferences).
    - `PetOwner`: store owner info (availability, preferences).
    - `Scheduler`: accept tasks, apply constraints/preferences from `Pet` and `PetOwner`, and produce a plan for display.

**b. Design changes**

Yes, several design changes were made during implementation to address bottlenecks and missing relationships:

- **Added Priority Enum**: Introduced a `Priority` enum class to enforce valid priority values ("low", "medium", "high") instead of accepting any string. This prevents runtime errors from typos and improves type safety.

- **Enhanced Task validation**: Expanded `Task.validate()` to check for empty titles, negative durations, invalid priorities, backwards time windows (end before start), and out-of-range times (outside 0-1440 minutes). This catches configuration errors early.

- **Added PetOwner → Pet relationship**: Added an optional `pet` field to `PetOwner` to represent the "owns" relationship shown in the UML. This makes the ownership explicit and allows for future features like accessing pet preferences through the owner.

- **Changed add_task() return type**: Modified `Scheduler.add_task()` from `None` to `bool` so callers can detect when a task fails validation instead of silently ignoring invalid tasks.

- **Added PlanItem.reason field**: Added a `reason: str` field to `PlanItem` to explain why each task was scheduled at its time (or why it couldn't be scheduled). This provides transparency in the scheduling decisions.

- **Added conflict detection logic**: Implemented `_check_time_overlap()` helper method and modified `generate_plan()` to detect and prevent overlapping task schedules. The scheduler now maintains a list of occupied time slots and finds non-conflicting windows.

- **Added task removal methods**: Added `remove_task()` and `clear_tasks()` methods to `Scheduler` because you could add tasks but never remove them, limiting flexibility during testing and updates.

 **Added validation in generate_plan()**: Changed `generate_plan()` to raise `ValueError` if pet or owner is not set, rather than silently returning an empty list. This gives clearer error messages when the scheduler is misconfigured.

- **Improved priority sorting**: Added `_get_priority_value()` helper to convert priority strings to numeric values for consistent sorting. Tasks are now sorted by priority first, then by duration (longer tasks scheduled first to maximize utilization).

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers multiple constraint types:

(1) **Time constraints** - task time windows, owner availability, task durations, and break times between tasks;

(2) **Priority constraints** - static priority levels (low/medium/high) plus dynamic urgency boosting for tasks within 120 minutes of their deadline;

(3) **Dependency constraints** - tasks with `depends_on` relationships must wait for prerequisite tasks; 

(4) **Flexibility constraints** - rigid tasks schedule first, flexible tasks only fill gaps ≥15 minutes; 

(5) **Validation constraints** - all tasks validated for empty titles, invalid durations, backwards time windows, etc.

I prioritized constraints in this hierarchy: dependencies first (can't give medicine before feeding), then priority level (high-priority tasks never bumped by low-priority), then duration optimization (longer tasks scheduled earlier to maximize utilization). Time windows and owner availability act as hard constraints that override all other considerations - tasks simply cannot be scheduled outside these bounds.

**b. Tradeoffs**

**Tradeoff: Greedy Scheduling vs. Global Optimization**

The scheduler uses a **greedy approach** that schedules tasks one-by-one in priority order (highest priority first), placing each task at the earliest available time slot. This trades **global optimality** for **simplicity and speed**.

**What we gain:**
- Fast execution: O(n²) time complexity instead of exponential for exhaustive search
- Simple, understandable logic that's easy to debug and maintain
- Predictable behavior: high-priority tasks are always scheduled first
- Real-time responsiveness: can generate a schedule in milliseconds

**Why this tradeoff is reasonable for pet care:**

1. **Urgency matters**: Pet care tasks often have real urgency (feeding a hungry pet, administering medication). A greedy priority-first approach ensures critical tasks never get bumped.

2. **Human interpretability**: Pet owners need to understand *why* tasks were scheduled in a certain order. "High priority tasks go first" is intuitive; "optimal by complex scoring function" is not.

3. **Dynamic schedules**: Pet owners frequently add/remove tasks throughout the day. A fast greedy algorithm allows instant rescheduling, while global optimization would be too slow for interactive use.

4. **Good enough is better than perfect**: Getting an 80% optimal schedule in milliseconds is more valuable than waiting seconds for a 95% optimal schedule when caring for pets.

---

## 3. AI Collaboration

**a. How you used AI**

I used AI extensively across all project phases: 

(1) **Design brainstorming** - exploring UML class relationships and deciding which attributes belong to Task vs Pet vs Owner; 

(2) **Implementation** - generating initial scheduling algorithm structure and conflict detection logic; 

(3) **Debugging** - fixing validation edge cases like backwards time windows and invalid priority strings; 

(4) **Refactoring** - adding advanced features like recurring tasks, gap-filling algorithms, and dynamic priority boosting.

The most helpful prompts were specific and context-rich: "Explain how to detect overlapping time slots efficiently" or "Suggest validation checks for a task scheduling system" worked much better than vague requests like "help me code this." Asking AI to explain the tradeoffs between different algorithms (greedy vs backtracking) was particularly valuable for making informed design decisions.

**b. Judgment and verification**

AI initially suggested implementing a backtracking algorithm with branch-and-bound optimization to find the global optimal schedule. While this would theoretically produce better schedules, I rejected it in favor of the simpler greedy approach because: 

(1) O(2^n) exponential time complexity would be too slow for interactive use, 

(2) the added complexity would make debugging much harder, and 

(3) for pet care, "good enough fast" beats "perfect slow."

I verified this decision by testing both approaches on sample schedules with 10+ tasks. The greedy algorithm completed in milliseconds with schedules that were 85-90% as efficient as brute-force optimal solutions. I also reasoned that pet owners need to understand *why* their schedule looks the way it does - "high priority first" is intuitive, while complex optimization scoring is opaque. The tradeoff analysis in section 2b documents this reasoning.

---

## 4. Testing and Verification

**a. What you tested**

I implemented two core tests: 

(1) `test_task_validation_and_details()` validates that the Task class correctly accepts valid inputs, enforces constraints via `validate()`, and returns accurate details including time string conversion ("09:00" → 540 minutes); 

(2) `test_pet_preferences()` verifies that Pet objects can store and retrieve preference key-value pairs correctly.

These tests are important because they validate foundational data integrity - if task validation fails, the scheduler could attempt to schedule invalid tasks (negative durations, backwards time windows) leading to crashes or incorrect plans. Similarly, pet preferences drive scheduling decisions (like morning exercise for dogs), so incorrect storage would silently produce wrong schedules. However, I acknowledge the test coverage is minimal and doesn't test the actual scheduling algorithms.

**b. Confidence**

I'm moderately confident (7/10) that the scheduler works correctly for typical use cases - task creation, validation, priority-based scheduling, and basic conflict detection all function as designed. However, the test coverage is insufficient (only 2 tests, neither covering scheduling logic), so edge cases may have bugs.

If I had more time, I'd test: 

(1) **Circular dependencies** - what happens if Task A depends on B which depends on A?; 

(2) **Gap-filling edge cases** - multiple flexible tasks competing for the same gap; 

(3) **Tasks entirely outside owner availability** - are they properly rejected?; 

(4) **Recurring task edge cases** - what if a daily task is added at 11:59 PM?; 

(5) **Dependency chains** - Task C depends on B depends on A, ensuring correct ordering; 

(6) **Dynamic priority boosting** - verifying urgency calculations near deadlines; 

(7) **Break time edge cases** - do breaks prevent scheduling when they shouldn't?

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the **modular class design** and **transparent scheduling explanations**. The separation of concerns (Task handles validation, Scheduler handles logic, PlanItem handles results) made the system easy to understand and extend - adding recurring tasks later required minimal changes to existing code. Even better, every PlanItem includes a `reason` field explaining *why* it was scheduled at that time ("Scheduled at earliest available slot" vs "Waiting for dependency: Feed pet"), which makes the system's decisions interpretable and debuggable. This transparency was crucial for identifying scheduling bugs and helps users understand their daily plan.

**b. What you would improve**

With another iteration, I would: 

(1) **Dramatically expand testing** - the current 2 tests are woefully insufficient; I need tests for every scheduling algorithm, conflict detection, dependency chains, and edge cases; 

(2) **Add circular dependency detection** - currently the system would infinite loop if Task A depends on Task B which depends on Task A; 

(3) **Implement limited backtracking** - when the greedy approach fails to schedule all high-priority tasks, try rearranging earlier tasks to make room; 

(4) **Proper multi-pet support** - currently the system tracks one pet, but pet owners often have multiple pets with conflicting needs; 

(5) **Optimize conflict detection** - the current O(n log n) approach could be improved with an interval tree for very large schedules.

**c. Key takeaway**

**Start simple, then optimize.** The most important lesson was resisting the temptation to build the "perfect" scheduler from day one. I initially wanted to implement complex optimization with backtracking, constraint satisfaction solvers, and machine learning for preference prediction. Instead, I built the simplest possible greedy algorithm first, validated it worked, *then* added features incrementally (dynamic priority, gap-filling, dependencies). This approach meant I always had a working system to test against, could measure the impact of each addition, and avoided getting lost in premature optimization. AI tools encouraged this too - when I asked "how do I build a scheduler," AI suggested starting with a simple priority queue before exploring advanced algorithms. The explicit tradeoff documentation in section 2b emerged from this philosophy: understand *why* you're choosing simplicity over optimality, and write it down.

## 6. Submission Notes

For this submission, the strongest AI feature is the RAG explanation layer in `knowledge_base.py` and `ai_explainer.py`, which changes how the app explains schedules instead of just displaying them. The most useful AI suggestion was to start with a greedy scheduler and add guardrails around validation and conflicts. The weakest suggestion was the idea of switching immediately to a backtracking optimizer, because it would have increased complexity without improving the interactive demo experience enough to justify the cost.

The main limitation I still see is test depth: the app is working end-to-end, but future work should add broader coverage for edge cases such as circular dependencies, multi-task tie-breaking, and larger schedules. If I continued the project, I would also expand the RAG layer to support more sources and add a small evaluation script that reports pass/fail results across multiple scenarios.
