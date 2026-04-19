"""
PawPal+ System - Core Classes

Centralized task, pet, owner, and scheduler logic used by the app.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _time_to_minutes(value: Optional[object]) -> Optional[int]:
    """Convert HH:MM strings or minutes to total minutes."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if ":" in text:
            hours_str, minutes_str = text.split(":", 1)
            if hours_str.isdigit() and minutes_str.isdigit():
                return int(hours_str) * 60 + int(minutes_str)
    return None


def _minutes_to_time(total_minutes: int) -> str:
    """Convert minutes since midnight to HH:MM text."""
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


class Task:
    """Represents a pet care task."""

    def __init__(
        self,
        title: str,
        task_type: str,
        duration_minutes: int,
        priority: str,
        time_window: Tuple[int, int] = (0, 1440),
        notes: str = "",
        start_time: Optional[object] = None,
        depends_on: Optional[str] = None,
        is_flexible: bool = False,
        completed: bool = False,
        frequency: Optional[str] = None,
    ):
        self.title = title
        self.task_type = task_type
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.time_window = time_window
        self.notes = notes
        self.start_time = _time_to_minutes(start_time)
        self.depends_on = depends_on
        self.is_flexible = is_flexible
        self.completed = completed
        self.frequency = frequency  # None, "daily", or "weekly"

    def validate(self) -> bool:  # sourcery skip: assign-if-exp, reintroduce-else
        """Validate task constraints."""
        if not self.title:
            return False
        if not (1 <= self.duration_minutes <= 1440):
            return False
        if self.priority not in ["low", "medium", "high"]:
            return False
        if self.time_window[0] >= self.time_window[1]:
            return False
        if self.start_time is None:
            return True
        return 0 <= self.start_time < 1440

    def get_details(self) -> Dict[str, object]:
        """Return task details as a dictionary."""
        return {
            "title": self.title,
            "type": self.task_type,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "time_window": self.time_window,
            "start_time": self.start_time,
            "notes": self.notes,
            "frequency": self.frequency,
        }

    def create_next_occurrence(self) -> Optional["Task"]:
        """
        Create a new instance of this task for the next occurrence (if recurring).
        
        This method is used for tasks with a frequency of "daily" or "weekly" to
        automatically generate the next task instance when the current one is completed.
        
        Returns:
            A new Task object with the same properties but completed=False if the task
            has a valid frequency ("daily" or "weekly"), None otherwise.
            
        Algorithm:
            - Checks if task has a valid frequency ("daily" or "weekly")
            - Creates a shallow copy of the task with all properties except completed
            - Sets completed=False for the new instance
            
        Time Complexity: O(1) - constant time to create a new task object
        """
        if not self.frequency or self.frequency not in ["daily", "weekly"]:
            return None

        return Task(
            title=self.title,
            task_type=self.task_type,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            time_window=self.time_window,
            notes=self.notes,
            start_time=self.start_time,
            depends_on=self.depends_on,
            is_flexible=self.is_flexible,
            completed=False,
            frequency=self.frequency,
        )

    def __repr__(self) -> str:
        freq_str = f", {self.frequency}" if self.frequency else ""
        return f"Task('{self.title}', {self.duration_minutes}min, {self.priority}{freq_str})"


class Pet:
    """Represents a pet with its characteristics and preferences."""

    def __init__(self, name: str, species: str, needs: Optional[List[str]] = None):
        self.name = name
        self.species = species
        self.needs = needs or []
        self.preferences: Dict[str, str] = {}

    def add_preference(self, key: str, value: str) -> None:
        """Add or update a preference for this pet."""
        self.preferences[key] = value

    def get_preferences(self) -> Dict[str, str]:
        """Return all preferences for this pet."""
        return self.preferences.copy()

    def __repr__(self) -> str:
        return f"Pet('{self.name}', {self.species})"


class PetOwner:
    """Represents a pet owner with availability and preferences."""

    def __init__(self, name: str, availability: Tuple[int, int] = (0, 1440)):
        self.name = name
        self.availability = availability
        self.preferences: Dict[str, str] = {}

    def add_preference(self, key: str, value: str) -> None:
        """Add or update a preference for this owner."""
        self.preferences[key] = value

    def get_preferences(self) -> Dict[str, str]:
        """Return all preferences for this owner."""
        return self.preferences.copy()

    def __repr__(self) -> str:
        return f"PetOwner('{self.name}')"


Owner = PetOwner


@dataclass
class PlanItem:
    """Represents a scheduled task in the daily plan."""

    task: Task
    scheduled_time: int
    duration_minutes: int
    reason: str = ""

    def get_summary(self) -> str:
        """Return a readable summary of this scheduled item."""
        hours = self.scheduled_time // 60
        minutes = self.scheduled_time % 60
        time_str = f"{hours:02d}:{minutes:02d}"
        return f"{time_str} - {self.task.title} ({self.duration_minutes}min)"

    def __repr__(self) -> str:
        return f"PlanItem('{self.task.title}' at {self.scheduled_time}min)"


class Scheduler:
    """
    Orchestrates pet care task scheduling.

    Accepts tasks and generates a daily plan based on:
    - Owner availability
    - Task priorities and time windows
    - Task dependencies
    - Gap filling with flexible tasks
    """

    def __init__(self, break_time_minutes: int = 5):
        self.tasks: List[Task] = []
        self.pet: Optional[Pet] = None
        self.owner: Optional[PetOwner] = None
        self.break_time_minutes = break_time_minutes

    def _has_task_with_title(self, title: str) -> bool:
        """Return True if a task with the provided title exists."""
        return any(existing.title == title for existing in self.tasks)

    def add_task(self, task: Task) -> bool:
        """Add a task to the scheduler."""
        if not task.validate():
            return False
        if task.depends_on:
            if task.depends_on == task.title:
                return False
            if not self._has_task_with_title(task.depends_on):
                return False
        self.tasks.append(task)
        return True

    def remove_task(self, task: Task) -> bool:
        """Remove a task from the scheduler."""
        if task not in self.tasks:
            return False
        self.tasks.remove(task)
        return True

    def set_pet(self, pet: Pet) -> None:
        """Set the pet for this scheduler."""
        self.pet = pet

    def set_owner(self, owner: PetOwner) -> None:
        """Set the owner for this scheduler."""
        self.owner = owner

    def sort_by_time(self) -> List[Task]:
        """
        Sort all tasks by their start_time attribute in ascending order.
        
        Tasks without a start_time (None) are placed at the end of the list.
        This is useful for displaying tasks in chronological order or detecting
        temporal patterns.
        
        Returns:
            A new sorted list of tasks. Tasks with earlier start times appear first.
            Tasks with start_time=None appear at the end.
            
        Algorithm:
            - Uses Python's built-in sorted() with a lambda key function
            - Tasks with None start_time get float('inf') as sort key (end of list)
            - Stable sort preserves order of tasks with equal start times
            
        Time Complexity: O(n log n) where n is the number of tasks
        Space Complexity: O(n) - creates a new sorted list
        """
        return sorted(
            self.tasks,
            key=lambda t: t.start_time if t.start_time is not None else float('inf')
        )

    def filter_tasks(
        self,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
    ) -> List[Task]:
        """
        Filter tasks by completion status and/or pet name.

        Args:
            completed: If True, return only completed tasks. If False, return only incomplete tasks.
                      If None, return all tasks regardless of completion status.
            pet_name: If provided, only return tasks for the pet with this name.
                     If None, return tasks regardless of pet association.

        Returns:
            List of tasks matching the filter criteria.
        """
        result = self.tasks[:]

        if completed is not None:
            result = [t for t in result if t.completed == completed]

        if pet_name is not None:
            result = result if self.pet and self.pet.name == pet_name else []
        return result

    def mark_task_complete(self, task: Task) -> Optional[Task]:
        # sourcery skip: use-named-expression
        """
        Mark a task as complete and create a new instance if it's recurring.

        Args:
            task: The task to mark as complete.

        Returns:
            A new Task instance if the task is recurring (daily/weekly), None otherwise.
        """
        if task not in self.tasks:
            return None
        
        task.completed = True
        
        # If the task is recurring, create the next occurrence
        if task.frequency in ["daily", "weekly"]:
            next_occurrence = task.create_next_occurrence()
            if next_occurrence:
                self.add_task(next_occurrence)
                return next_occurrence
        
        return None

    def _tasks_overlap(self, task1: Task, task2: Task) -> Optional[int]:
        """
        Check if two tasks overlap in time.
        
        Args:
            task1: First task to compare.
            task2: Second task to compare.
        
        Returns:
            The overlap duration in minutes, or None if no overlap.
        """
        if task1.start_time is None or task2.start_time is None:
            return None
        
        task1_end = task1.start_time + task1.duration_minutes
        task2_end = task2.start_time + task2.duration_minutes
        
        # Calculate overlap: find the latest start and earliest end
        overlap_start = max(task1.start_time, task2.start_time)
        overlap_end = min(task1_end, task2_end)
        
        overlap_duration = overlap_end - overlap_start
        return overlap_duration if overlap_duration > 0 else None

    def detect_scheduling_conflicts(self) -> List[str]:
        """
        Detect if any two tasks are scheduled at overlapping times.
        
        Uses optimized approach:
        - Sorts tasks by start time for faster comparison
        - Early exit when tasks no longer overlap
        - Lightweight warnings (never crashes the program)
        
        Returns:
            List of warning messages describing scheduling conflicts.
            Empty list if no conflicts are detected.
        """
        conflicts: List[str] = []
        
        # Filter and sort tasks by start_time for O(n log n) performance
        sorted_tasks = sorted(
            [t for t in self.tasks if t.start_time is not None],
            key=lambda t: t.start_time or 0
        )
        
        # Compare only relevant task pairs
        for i, task1 in enumerate(sorted_tasks):
            for task2 in sorted_tasks[i + 1:]:
                # Early exit: if task2 starts after task1 ends, no more overlaps possible
                if task2.start_time >= task1.start_time + task1.duration_minutes:
                    break
                
                # Check overlap using helper method
                overlap_minutes = self._tasks_overlap(task1, task2)
                if overlap_minutes:
                    time_str1 = f"{task1.start_time // 60:02d}:{task1.start_time % 60:02d}"
                    time_str2 = f"{task2.start_time // 60:02d}:{task2.start_time % 60:02d}"
                    
                    pet_info = f" for {self.pet.name}" if self.pet else ""
                    
                    warning = (
                        f"⚠️  SCHEDULING CONFLICT{pet_info}: "
                        f"'{task1.title}' ({time_str1}, {task1.duration_minutes}min) "
                        f"overlaps with '{task2.title}' ({time_str2}, {task2.duration_minutes}min) "
                        f"by {overlap_minutes} minutes"
                    )
                    conflicts.append(warning)
        
        return conflicts

    def _get_dynamic_priority(self, task: Task, current_time: int) -> float:
        """
        Calculate a dynamic priority score that increases as deadlines approach.
        
        This method converts the task's base priority ("high", "medium", "low") into
        a numeric value and adds an urgency boost if the task is approaching its
        deadline (within 2 hours of the time window end).
        
        Args:
            task: The task to calculate priority for.
            current_time: Current time in minutes since midnight (0-1439).
            
        Returns:
            A float priority score between 1.0 and 4.0:
            - Base: 3.0 (high), 2.0 (medium), 1.0 (low)
            - Urgency boost: up to +1.0 if deadline < 120 minutes away
            
        Algorithm:
            1. Map priority string to base numeric value (high=3.0, medium=2.0, low=1.0)
            2. Calculate time until deadline (time_window[1] - current_time)
            3. If deadline is within 120 minutes, add urgency boost:
               boost = 1.0 - (time_until_deadline / 120.0)
            4. Return combined priority value
            
        Time Complexity: O(1) - constant time calculations
        """
        base_priority = {"high": 3.0, "medium": 2.0, "low": 1.0}
        priority_value = base_priority.get(task.priority, 1.0)

        time_until_deadline = task.time_window[1] - current_time
        if 0 < time_until_deadline < 120:
            urgency_boost = 1.0 - (time_until_deadline / 120.0)
            priority_value += urgency_boost

        return priority_value

    def _check_dependencies(self, task: Task, scheduled_tasks: List[Task]) -> bool:
        """
        Check if a task's dependencies have been satisfied.
        
        A task can only be scheduled if its dependency (another task) has already
        been scheduled. This ensures proper ordering (e.g., "Give medication" must
        come after "Feed pet").
        
        Args:
            task: The task to check dependencies for.
            scheduled_tasks: List of tasks that have already been scheduled.
            
        Returns:
            True if the task has no dependencies or its dependency has been scheduled,
            False otherwise.
            
        Algorithm:
            1. If task.depends_on is None/empty, return True (no dependencies)
            2. Check if any scheduled task has a title matching task.depends_on
            3. Return True if match found, False otherwise
            
        Time Complexity: O(n) where n is the number of scheduled tasks
        """
        if not task.depends_on:
            return True
        return any(t.title == task.depends_on for t in scheduled_tasks)

    def _try_schedule_at(
        self, task: Task, start_time: int, occupied_slots: List[Tuple[int, int]]
    ) -> bool:
        """
        Check if a task can be scheduled at a specific time without conflicts.
        
        Verifies that scheduling the task at the given start_time would not overlap
        with any existing occupied time slots.
        
        Args:
            task: The task to schedule.
            start_time: Proposed start time in minutes since midnight.
            occupied_slots: List of (start, end) tuples representing busy time ranges.
            
        Returns:
            True if the task can fit without overlapping occupied slots, False otherwise.
            
        Algorithm:
            1. Calculate task end_time = start_time + duration_minutes
            2. For each occupied slot [slot_start, slot_end):
               - Check if intervals overlap: start_time < slot_end AND end_time > slot_start
               - If overlap detected, return False
            3. If no overlaps found, return True
            
        Time Complexity: O(s) where s is the number of occupied slots
        """
        end_time = start_time + task.duration_minutes

        for slot_start, slot_end in occupied_slots:
            if start_time < slot_end and end_time > slot_start:
                return False
        return True

    def _find_best_time(
        self,
        task: Task,
        earliest_start: int,
        latest_end: int,
        occupied_slots: List[Tuple[int, int]],
    ) -> Optional[int]:
        """
        Find the best available time slot for a task using incremental search.
        
        Attempts to schedule the task as early as possible within its valid time range,
        trying 15-minute increments if the earliest_start slot is occupied.
        
        Args:
            task: The task to find a time slot for.
            earliest_start: Earliest allowed start time (in minutes).
            latest_end: Latest allowed end time (in minutes).
            occupied_slots: List of (start, end) tuples representing busy time ranges.
            
        Returns:
            The start time (in minutes) if a valid slot is found, None if no slot available.
            
        Algorithm:
            1. Try earliest_start first (greedy approach)
            2. If occupied, try earliest_start + 15, earliest_start + 30, etc.
            3. Search up to 120 minutes ahead in 15-minute increments
            4. For each candidate:
               - Verify task would end by latest_end
               - Check for conflicts using _try_schedule_at()
            5. Return first available slot or None if all attempts fail
            
        Time Complexity: O(k * s) where k is search depth (up to 8 attempts) 
                        and s is number of occupied slots
        """
        latest_start = latest_end - task.duration_minutes
        if earliest_start > latest_start:
            return None

        if self._try_schedule_at(task, earliest_start, occupied_slots):
            return earliest_start

        for candidate_start in range(earliest_start + 15, latest_start + 1, 15):
            if self._try_schedule_at(task, candidate_start, occupied_slots):
                return candidate_start

        return None

    def _fill_gaps(
        self,
        plan: List[PlanItem],
        flexible_tasks: List[Task],
        owner_availability: Tuple[int, int],
    ) -> List[PlanItem]:
        """
        Fill empty time gaps in the schedule with flexible tasks.
        
        Identifies gaps between scheduled rigid tasks and attempts to fit flexible
        tasks into those gaps to maximize schedule utilization. Only gaps of 15+ minutes
        are considered.
        
        Args:
            plan: Current list of scheduled plan items.
            flexible_tasks: List of tasks marked as is_flexible=True.
            owner_availability: Tuple (start_time, end_time) of owner's available hours.
            
        Returns:
            Updated plan with flexible tasks added to available gaps.
            
        Algorithm:
            1. Sort scheduled items by time
            2. Identify gaps:
               - Between owner availability start and first task
               - Between consecutive tasks (accounting for break_time_minutes)
               - Between last task and owner availability end
            3. For each gap ≥ 15 minutes:
               - Find first flexible task that fits the gap duration and time window
               - Schedule it at gap_start
               - Remove from flexible_tasks list
            4. Return original plan + newly scheduled flexible tasks
            
        Time Complexity: O(n log n + g * f) where n is scheduled items, g is gaps, 
                        f is flexible tasks
        Space Complexity: O(g) for storing identified gaps
        """
        if not flexible_tasks:
            return plan

        scheduled_items = [item for item in plan if item.scheduled_time >= 0]
        scheduled_items.sort(key=lambda x: x.scheduled_time)

        gaps: List[Tuple[int, int]] = []
        current = owner_availability[0]

        for item in scheduled_items:
            if item.scheduled_time > current:
                gap_duration = item.scheduled_time - current
                if gap_duration >= 15:
                    gaps.append((current, item.scheduled_time))
            current = max(
                current,
                item.scheduled_time + item.duration_minutes + self.break_time_minutes,
            )

        if current < owner_availability[1]:
            gap_duration = owner_availability[1] - current
            if gap_duration >= 15:
                gaps.append((current, owner_availability[1]))

        additional_items: List[PlanItem] = []
        for gap_start, gap_end in gaps:
            gap_duration = gap_end - gap_start
            for task in list(flexible_tasks):
                if task.duration_minutes <= gap_duration:
                    if (
                        task.time_window[0] <= gap_start
                        and gap_start + task.duration_minutes <= task.time_window[1]
                    ):
                        additional_items.append(
                            PlanItem(
                                task=task,
                                scheduled_time=gap_start,
                                duration_minutes=task.duration_minutes,
                                reason=f"Gap-filled during {gap_duration}min window",
                            )
                        )
                        flexible_tasks.remove(task)
                        break

        return plan + additional_items

    def generate_plan(self) -> List[PlanItem]:
        """
        Generate an optimized daily schedule for all tasks.
        
        This is the main scheduling algorithm that orchestrates task scheduling based on
        priorities, time windows, dependencies, and owner availability. It uses a greedy
        approach to schedule rigid tasks first, then fills gaps with flexible tasks.
        
        Returns:
            List of PlanItem objects representing the daily schedule. Scheduled items
            appear first (sorted by time), followed by unscheduled items. Returns empty
            list if pet or owner is not set, or if there are no tasks.
            
        Algorithm (Greedy Scheduling):
            1. Validate preconditions (pet, owner, tasks exist)
            2. Separate tasks into rigid and flexible lists
            3. Sort rigid tasks by:
               - Dynamic priority (higher first, with urgency boost)
               - Duration (longer first, for better slot utilization)
            4. For each rigid task in priority order:
               a. Check dependencies - skip if not satisfied
               b. Calculate valid scheduling window (intersection of task window & owner availability)
               c. Find best available time slot using _find_best_time()
               d. If slot found: schedule task, mark slot occupied, add break time
               e. If no slot: mark task as unscheduled with reason
            5. Fill remaining gaps with flexible tasks using _fill_gaps()
            6. Sort scheduled items by time, append unscheduled items at end
            
        Considerations:
            - Pet species-specific recommendations (e.g., morning walks for dogs)
            - Task dependencies must be satisfied in order
            - Break time added between consecutive tasks
            - Conflict-free scheduling via occupied_slots tracking
            
        Time Complexity: O(n² log n) where n is number of tasks
            - O(n log n) for sorting
            - O(n²) for scheduling loop (n tasks * checking occupied slots)
            - O(n log n + g*f) for gap filling where g=gaps, f=flexible tasks
            
        Space Complexity: O(n) for storing plan items and occupied slots
        """
        if not self.pet or not self.owner:
            return []

        if not self.tasks:
            return []

        rigid_tasks = [t for t in self.tasks if not t.is_flexible]
        flexible_tasks = [t for t in self.tasks if t.is_flexible]

        priority_reference_time = self.owner.availability[0]
        sorted_tasks = sorted(
            rigid_tasks,
            key=lambda t: (
                self._get_dynamic_priority(t, priority_reference_time),
                t.duration_minutes,
            ),
            reverse=True,
        )

        plan: List[PlanItem] = []
        scheduled_tasks: List[Task] = []
        occupied_slots: List[Tuple[int, int]] = []
        owner_end = self.owner.availability[1]

        pending_tasks = sorted_tasks[:]
        while pending_tasks:
            progress_made = False
            deferred_tasks: List[Task] = []

            for task in pending_tasks:
                if not self._check_dependencies(task, scheduled_tasks):
                    deferred_tasks.append(task)
                    continue

                task_start = task.time_window[0]
                task_end = task.time_window[1]

                earliest_start = max(task_start, self.owner.availability[0])
                latest_end = min(owner_end, task_end)

                if earliest_start + task.duration_minutes > latest_end:
                    plan.append(
                        PlanItem(
                            task=task,
                            scheduled_time=-1,
                            duration_minutes=task.duration_minutes,
                            reason="Task time window doesn't overlap with owner availability",
                        )
                    )
                    progress_made = True
                    continue

                best_start = self._find_best_time(
                    task, earliest_start, latest_end, occupied_slots
                )

                if best_start is not None:
                    end_time = best_start + task.duration_minutes

                    time_desc = _minutes_to_time(best_start)
                    if best_start > earliest_start:
                        reason = (
                            f"Scheduled at {time_desc} ({task.priority} priority, "
                            "adjusted to avoid conflicts)"
                        )
                    else:
                        reason = (
                            f"Scheduled at {time_desc} ({task.priority} priority, "
                            "optimal time)"
                        )

                    if self.pet.species == "dog" and task.task_type == "walk" and best_start < 600:
                        reason += " - dogs benefit from morning exercise"

                    if task.priority == "high" and task.time_window[0] >= 1020:
                        window_start = _minutes_to_time(task.time_window[0])
                        window_end = _minutes_to_time(task.time_window[1])
                        reason += (
                            f" - kept inside evening window {window_start}-{window_end}"
                        )

                    plan_item = PlanItem(
                        task=task,
                        scheduled_time=best_start,
                        duration_minutes=task.duration_minutes,
                        reason=reason,
                    )
                    plan.append(plan_item)
                    scheduled_tasks.append(task)
                    occupied_slots.append((best_start, end_time + self.break_time_minutes))
                    progress_made = True
                else:
                    hours_needed = task.duration_minutes / 60
                    plan.append(
                        PlanItem(
                            task=task,
                            scheduled_time=-1,
                            duration_minutes=task.duration_minutes,
                            reason=f"No available {hours_needed:.1f}h slot in preferred time window",
                        )
                    )
                    progress_made = True

            if not deferred_tasks:
                break

            if not progress_made:
                for task in deferred_tasks:
                    plan.append(
                        PlanItem(
                            task=task,
                            scheduled_time=-1,
                            duration_minutes=task.duration_minutes,
                            reason=f"Waiting for dependency: {task.depends_on}",
                        )
                    )
                break

            pending_tasks = deferred_tasks

        plan = self._fill_gaps(plan, flexible_tasks, self.owner.availability)

        scheduled = [p for p in plan if p.scheduled_time >= 0]
        unscheduled = [p for p in plan if p.scheduled_time < 0]
        scheduled.sort(key=lambda x: x.scheduled_time)

        return scheduled + unscheduled

    def __repr__(self) -> str:
        return f"Scheduler({len(self.tasks)} tasks, pet={self.pet}, owner={self.owner})"
