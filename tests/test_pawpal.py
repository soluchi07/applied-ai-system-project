"""Basic tests for PawPal+ core classes."""

from pawpal_system import Pet, PetOwner, Scheduler, Task


def test_task_validation_and_details() -> None:
	"""Task validation returns true for valid inputs."""
	task = Task(
		title="Check water",
		task_type="other",
		duration_minutes=5,
		priority="medium",
		time_window=(540, 600),
		start_time="09:00",
	)

	assert task.validate() is True
	details = task.get_details()
	assert details["title"] == "Check water"
	assert details["start_time"] == 540


def test_pet_preferences() -> None:
	"""Pets store and return preferences."""
	pet = Pet(name="Mochi", species="dog")
	pet.add_preference("favorite_time", "morning")

	preferences = pet.get_preferences()
	assert preferences["favorite_time"] == "morning"


def test_high_priority_evening_task_stays_in_evening_window() -> None:
	scheduler = Scheduler()
	scheduler.set_pet(Pet("Mochi", "dog"))
	scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

	assert scheduler.add_task(
		Task("Evening medication", "other", 30, "high", time_window=(1080, 1260))
	)
	assert scheduler.add_task(
		Task("Morning walk", "walk", 30, "high", time_window=(480, 660))
	)

	plan = scheduler.generate_plan()
	evening_item = next(item for item in plan if item.task.title == "Evening medication")

	assert evening_item.scheduled_time >= 1080
	assert "kept inside evening window" in evening_item.reason


def test_evening_window_task_does_not_block_morning_task() -> None:
	scheduler = Scheduler()
	scheduler.set_pet(Pet("Mochi", "dog"))
	scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

	assert scheduler.add_task(
		Task("Evening grooming", "groom", 60, "high", time_window=(1080, 1260))
	)
	assert scheduler.add_task(
		Task("Breakfast", "feed", 15, "medium", time_window=(510, 720))
	)

	plan = scheduler.generate_plan()
	breakfast_item = next(item for item in plan if item.task.title == "Breakfast")

	assert breakfast_item.scheduled_time != -1
	assert breakfast_item.scheduled_time < 720


def test_dependency_order_keeps_medication_after_feed() -> None:
	scheduler = Scheduler()
	scheduler.set_pet(Pet("Mochi", "dog"))
	scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

	assert scheduler.add_task(Task("Feed pet", "feed", 15, "high", time_window=(540, 720)))
	assert scheduler.add_task(
		Task(
			"Give medication",
			"med",
			10,
			"high",
			time_window=(540, 780),
			depends_on="Feed pet",
		)
	)

	plan = scheduler.generate_plan()
	feed_item = next(item for item in plan if item.task.title == "Feed pet")
	med_item = next(item for item in plan if item.task.title == "Give medication")

	assert feed_item.scheduled_time != -1
	assert med_item.scheduled_time != -1
	assert med_item.scheduled_time > feed_item.scheduled_time
	assert "dependency" not in med_item.reason.lower()


def test_conflicts_are_reported_without_crashing_scheduler() -> None:
	scheduler = Scheduler()
	scheduler.set_pet(Pet("Mochi", "dog"))
	scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

	assert scheduler.add_task(Task("Morning walk", "walk", 30, "high", start_time="09:00"))
	assert scheduler.add_task(Task("Breakfast", "feed", 20, "medium", start_time="09:10"))

	conflicts = scheduler.detect_scheduling_conflicts()

	assert conflicts
	assert "Morning walk" in conflicts[0]
	assert "Breakfast" in conflicts[0]


def test_add_task_rejects_unknown_dependency() -> None:
	scheduler = Scheduler()

	dependent = Task(
		title="Give medication",
		task_type="med",
		duration_minutes=10,
		priority="high",
		time_window=(540, 780),
		depends_on="Feed pet",
	)

	assert scheduler.add_task(dependent) is False


def test_add_task_rejects_self_dependency() -> None:
	scheduler = Scheduler()

	self_dependent = Task(
		title="Feed pet",
		task_type="feed",
		duration_minutes=15,
		priority="high",
		time_window=(540, 720),
		depends_on="Feed pet",
	)

	assert scheduler.add_task(self_dependent) is False


def test_remove_task_removes_existing_task() -> None:
	scheduler = Scheduler()
	task = Task("Water refill", "other", 5, "low", time_window=(540, 1140))

	assert scheduler.add_task(task)
	assert scheduler.remove_task(task) is True
	assert task not in scheduler.tasks


def test_mark_task_complete_creates_next_daily_occurrence() -> None:
	scheduler = Scheduler()
	recurring_task = Task(
		title="Evening medication",
		task_type="med",
		duration_minutes=10,
		priority="high",
		time_window=(1080, 1260),
		frequency="daily",
	)

	assert scheduler.add_task(recurring_task)
	next_task = scheduler.mark_task_complete(recurring_task)

	assert recurring_task.completed is True
	assert next_task is not None
	assert next_task is not recurring_task
	assert next_task.title == recurring_task.title
	assert next_task.frequency == "daily"
	assert next_task.completed is False
	assert next_task in scheduler.tasks


def test_mark_task_complete_non_recurring_returns_none() -> None:
	scheduler = Scheduler()
	non_recurring = Task(
		title="Brush coat",
		task_type="groom",
		duration_minutes=15,
		priority="medium",
		time_window=(900, 1080),
	)

	assert scheduler.add_task(non_recurring)
	next_task = scheduler.mark_task_complete(non_recurring)

	assert non_recurring.completed is True
	assert next_task is None


def test_dependency_task_is_deferred_then_scheduled_after_prerequisite() -> None:
	scheduler = Scheduler()
	scheduler.set_pet(Pet("Mochi", "dog"))
	scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

	assert scheduler.add_task(
		Task("Feed pet", "feed", 15, "medium", time_window=(540, 720))
	)
	assert scheduler.add_task(
		Task(
			"Give medication",
			"med",
			10,
			"high",
			time_window=(540, 780),
			depends_on="Feed pet",
		)
	)

	plan = scheduler.generate_plan()
	feed_item = next(item for item in plan if item.task.title == "Feed pet")
	med_item = next(item for item in plan if item.task.title == "Give medication")

	assert feed_item.scheduled_time >= 0
	assert med_item.scheduled_time >= 0
	assert med_item.scheduled_time > feed_item.scheduled_time
