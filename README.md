# PawPal+ (Module 2 Project)

I built **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

## What I Built

My final app was able to:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors


## Features

PawPal+ implements several sophisticated algorithms to optimize pet care scheduling:

### 1. Greedy Priority-Based Scheduling
The core `generate_plan()` algorithm uses a greedy approach to build optimal daily schedules:
- **Time Complexity**: O(n² log n) for n tasks
- **Strategy**: Schedules high-priority rigid tasks first, then fills gaps with flexible tasks
- **Considerations**: Owner availability, task time windows, dependencies, and pet species needs
- **Process**: Sorts tasks by dynamic priority and duration, then attempts to schedule each in the best available time slot

### 2. Dynamic Priority Calculation
Tasks receive priority scores that adapt based on urgency:
- **Base Priority**: High (3.0), Medium (2.0), Low (1.0)
- **Urgency Boost**: Up to +1.0 when deadline is within 120 minutes
- **Formula**: `priority_value + (1.0 - time_until_deadline / 120.0)`
- **Time Complexity**: O(1)
- Ensures critical deadlines are never missed by elevating priority as time runs out

### 3. Dependency Management
Enforces task ordering constraints (e.g., "Give medication" must follow "Feed pet"):
- **Validation**: `_check_dependencies()` verifies all prerequisites are met before scheduling
- **Time Complexity**: O(n) per check
- Automatically defers tasks with unsatisfied dependencies

### 4. Gap-Filling Algorithm
Maximizes schedule efficiency by utilizing free time:
- **Process**: Identifies gaps ≥15 minutes between rigid tasks
- **Strategy**: Fits flexible tasks into available gaps within their time windows
- **Time Complexity**: O(n log n + g·f) where g=gaps, f=flexible tasks
- Ensures no wasted time while respecting task constraints

### 5. Conflict Detection
Identifies overlapping tasks with an optimized algorithm:
- **Method**: `detect_scheduling_conflicts()` uses sorted comparison
- **Time Complexity**: O(n log n) with early exit optimization
- **Features**: 
  - Sorts tasks by start time for efficient comparison
  - Early termination when no more overlaps are possible
  - Returns human-readable warnings with exact overlap duration
- **Behavior**: Non-blocking warnings (never crashes the scheduler)

### 6. Incremental Time Slot Search
Finds optimal scheduling times with flexibility:
- **Method**: `_find_best_time()` attempts earliest fit, then searches in 15-minute increments
- **Search Depth**: Up to 120 minutes ahead
- **Time Complexity**: O(k·s) where k=attempts (max 8), s=occupied slots
- Balances preference for early scheduling with conflict avoidance

### 7. Recurring Task Management
Automates routine care with intelligent task regeneration:
- **Frequencies**: Daily and weekly recurrence patterns
- **Auto-Regeneration**: `mark_task_complete()` creates next occurrence when task is completed
- **Time Complexity**: O(1) for task regeneration
- Perfect for feeding schedules, walks, medication, and grooming

### 8. Task Organization Utilities
Provides flexible task management:
- **Sorting**: `sort_by_time()` orders tasks chronologically (O(n log n))
- **Filtering**: `filter_tasks()` by completion status and pet name
- **Validation**: Built-in constraint checking on all tasks

## Smarter Scheduling

PawPal+ now includes advanced scheduling features:

## RAG-Powered AI Advisor

PawPal+ now includes a retrieval-augmented explanation layer that grounds AI output in a pet-care knowledge base.

- `knowledge_base.py` stores curated care facts and performs semantic retrieval (top-3 facts per task)
- `ai_explainer.py` sends the schedule + retrieved facts to Gemini for grounded reasoning
- `app.py` renders:
  - schedule output from the scheduler
  - AI explanation section
  - multi-turn follow-up Q&A tied to the current generated plan
- `logging_config.py` configures console + file logs in `pawpal_execution.log`

### Guardrails and Reliability

- If retrieval returns no relevant facts for a task, the app explicitly says no specific guideline was retrieved
- If Gemini is unavailable (missing key/network/API error), the app falls back to local explanation logic
- Retrieval operations and model-call outcomes are logged for debugging and reproducibility

### Demo Scenarios

Use these examples to verify the end-to-end Streamlit flow:

1. **Morning dog routine**
  - Owner: Jordan
  - Pet: Mochi the dog
  - Tasks: Morning walk, Breakfast, Medication
  - Expected result: the walk is scheduled early, breakfast follows available time, and the explanation references dog exercise guidance from the knowledge base.

2. **Evening care window**
  - Owner: Jordan
  - Pet: Mochi the dog
  - Tasks: Evening grooming, Medication, Water refill
  - Expected result: tasks stay inside their time windows, conflict warnings appear if two tasks overlap, and the explanation highlights why evening tasks were kept in the late window.

3. **Dependency check**
  - Owner: Jordan
  - Pet: Mochi the dog
  - Tasks: Feed pet, Give medication (depends on Feed pet)
  - Expected result: the scheduler keeps medication after feeding, and the AI explanation uses the retrieved context to justify that ordering.

### Sample Input / Output

Sample input in the UI:

- Owner name: `Jordan`
- Pet name: `Mochi`
- Species: `Dog`
- Tasks:
  - `Morning walk` (30 min, high priority, 08:00-11:40)
  - `Breakfast` (15 min, medium priority, 09:00-12:00)
  - `Medication` (10 min, high priority, 09:30-10:30, depends on Breakfast)

Sample output:

- `Morning walk` is scheduled first because it is high priority and dogs benefit from morning exercise.
- `Breakfast` is placed inside its window without conflict.
- `Medication` stays after `Breakfast` because the dependency guardrail keeps prerequisite tasks in order.
- The AI explanation cites retrieved pet-care facts and falls back cleanly if Gemini is unavailable.

### Recurring Tasks
- **Daily & Weekly Tasks**: Mark tasks with `frequency="daily"` or `frequency="weekly"`
- **Auto-Regeneration**: When a recurring task is marked complete, a new instance is automatically created for the next occurrence
- Perfect for routine care like feeding, walks, and medication

### Task Management
- **Sort by Time**: `sort_by_time()` method returns tasks in chronological order
- **Smart Filtering**: `filter_tasks()` allows filtering by:
  - Completion status (completed/incomplete)
  - Pet name (for multi-pet households)
- **Completion Tracking**: Built-in `completed` attribute on all tasks

### Conflict Detection
- **Lightweight Warnings**: `detect_scheduling_conflicts()` identifies overlapping tasks without crashing
- **Optimized Algorithm**: 
  - Sorts tasks by start time (O(n log n))
  - Early exit optimization reduces unnecessary comparisons
  - Returns human-readable warning messages with exact overlap duration
- **Proactive Prevention**: Catches scheduling conflicts before they become problems

### Performance Optimizations
- Helper method `_tasks_overlap()` for cleaner, reusable overlap logic
- Greedy scheduling algorithm balances speed with effectiveness
- Gap-filling for flexible tasks maximizes schedule utilization

All core scheduling methods now include comprehensive docstrings with algorithm explanations and complexity analysis.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Set your Gemini API key before running the app:

```bash
export GEMINI_API_KEY="your_key_here"  # macOS/Linux
set GEMINI_API_KEY=your_key_here        # Windows cmd
$env:GEMINI_API_KEY="your_key_here"    # Windows PowerShell
```

You can also place keys in a local `.env` file (for example `GEMINI_API_KEY=...`).
PawPal+ auto-loads `.env` at startup.

`GOOGLE_API_KEY` is also accepted for compatibility. If no key is set, PawPal+ still runs and uses local fallback explanations.

### Run

```bash
streamlit run app.py
```

### Test

```bash
python -m pytest -q
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

### 📸 Demo
<a href="/course_images/ai110/your_screenshot_name.png" target="_blank"><img src='/course_images/ai110/demo.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>