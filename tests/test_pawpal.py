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
