"""
tests/test_pawpal.py
Unit tests for PawPal+ — happy paths and edge cases.

Test plan (from codebase edge-case analysis):

  Happy paths
  -----------
  1. Adding a task increases the pet's task count.
  2. mark_complete() flips completed to True and returns True.
  3. High-priority tasks appear before low-priority tasks in the plan.
  4. get_all_tasks() aggregates tasks across multiple pets.
  5. get_available_minutes() returns the correct window size.

  Edge cases
  ----------
  6.  Pet with no tasks        → build_plan() returns [] without crashing.
  7.  Owner with no pets       → build_plan() returns [] without crashing.
  8.  Task too long to fit     → oversized task skipped; smaller ones still schedule.
  9.  Species filter mismatch  → dog task not scheduled for a cat.
  10. Cache invalidation       → after mark_complete(), rebuilt plan excludes done task.
  11. preferred_hour past      → clock does not rewind; task starts at current pointer.
  12. All tasks completed      → build_plan() returns [].
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import CareTask, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Shared helpers — keep test bodies short and readable
# ---------------------------------------------------------------------------

def make_owner(start=8, end=20) -> Owner:
    return Owner(name="TestOwner", available_start=start, available_end=end)

def make_pet(name="Buddy", species="dog") -> Pet:
    return Pet(name=name, species=species, age=2)

def make_task(title="Walk", duration=30, priority="medium", **kwargs) -> CareTask:
    return CareTask(title=title, duration_minutes=duration, priority=priority, **kwargs)


# ---------------------------------------------------------------------------
# Happy path 1 — task addition
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """Pet.add_task() increments len(pet.tasks) for each call."""
    pet = make_pet()
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Walk"))
    assert len(pet.tasks) == 1
    pet.add_task(make_task("Feed"))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Happy path 2 — mark_complete
# ---------------------------------------------------------------------------

def test_mark_complete_changes_task_status():
    """Scheduler.mark_complete() sets completed=True on the named task."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(make_task("Morning walk"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    assert pet.tasks[0].completed is False

    result = scheduler.mark_complete("Morning walk")

    assert result is True
    assert pet.tasks[0].completed is True


# ---------------------------------------------------------------------------
# Happy path 3 — priority ordering
# ---------------------------------------------------------------------------

def test_high_priority_scheduled_before_low():
    """build_plan() places high-priority tasks before low-priority ones."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(make_task("Low task",  priority="low",  duration=10))
    pet.add_task(make_task("High task", priority="high", duration=10))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    titles = [e.task.title for e in plan]

    assert titles.index("High task") < titles.index("Low task")


# ---------------------------------------------------------------------------
# Happy path 4 — multi-pet task aggregation
# ---------------------------------------------------------------------------

def test_get_all_tasks_spans_multiple_pets():
    """Owner.get_all_tasks() returns tasks belonging to every pet."""
    owner = make_owner()
    dog = make_pet("Rex",   "dog")
    cat = make_pet("Luna",  "cat")
    dog.add_task(make_task("Walk the dog"))
    cat.add_task(make_task("Clean litter"))
    cat.add_task(make_task("Brush coat"))
    owner.add_pet(dog)
    owner.add_pet(cat)

    assert len(owner.get_all_tasks()) == 3


# ---------------------------------------------------------------------------
# Happy path 5 — available minutes
# ---------------------------------------------------------------------------

def test_get_available_minutes_correct():
    """Owner.get_available_minutes() returns (end - start) * 60."""
    owner = make_owner(start=8, end=20)
    assert owner.get_available_minutes() == 720


# ---------------------------------------------------------------------------
# Edge case 6 — pet with no tasks
# ---------------------------------------------------------------------------

def test_pet_with_no_tasks_returns_empty_plan():
    """build_plan() returns [] without crashing when the pet has no tasks."""
    owner = make_owner()
    owner.add_pet(make_pet())   # no tasks added

    assert Scheduler(owner).build_plan() == []


# ---------------------------------------------------------------------------
# Edge case 7 — owner with no pets
# ---------------------------------------------------------------------------

def test_owner_with_no_pets_returns_empty_plan():
    """build_plan() returns [] without crashing when the owner has no pets."""
    assert Scheduler(make_owner()).build_plan() == []


# ---------------------------------------------------------------------------
# Edge case 8 — task too long to fit
# ---------------------------------------------------------------------------

def test_oversized_task_is_skipped():
    """A task longer than the window is skipped; shorter tasks still schedule."""
    owner = make_owner(start=8, end=9)   # only 60 minutes
    pet = make_pet()
    pet.add_task(make_task("Huge task",  duration=90, priority="high"))
    pet.add_task(make_task("Short task", duration=20, priority="low"))
    owner.add_pet(pet)

    titles = [e.task.title for e in Scheduler(owner).build_plan()]

    assert "Huge task"  not in titles
    assert "Short task" in titles


# ---------------------------------------------------------------------------
# Edge case 9 — species filter mismatch
# ---------------------------------------------------------------------------

def test_species_filtered_task_excluded_for_wrong_species():
    """A dog-filtered task must not appear in a cat's schedule."""
    owner = make_owner()
    cat = make_pet("Whiskers", species="cat")
    cat.add_task(make_task("Dog bath",  duration=20, priority="high", species_filter="dog"))
    cat.add_task(make_task("Cat brush", duration=10, priority="high", species_filter="cat"))
    owner.add_pet(cat)

    titles = [e.task.title for e in Scheduler(owner).build_plan()]

    assert "Dog bath"  not in titles
    assert "Cat brush" in titles


# ---------------------------------------------------------------------------
# Edge case 10 — cache invalidation after mark_complete
# ---------------------------------------------------------------------------

def test_mark_complete_removes_task_from_rebuilt_plan():
    """After mark_complete(), the next build_plan() excludes the done task."""
    owner = make_owner()
    pet = make_pet()
    pet.add_task(make_task("Walk", duration=20, priority="high"))
    pet.add_task(make_task("Feed", duration=10, priority="medium"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    scheduler.build_plan()          # warm the cache

    scheduler.mark_complete("Walk") # must bust cache

    titles = [e.task.title for e in scheduler.build_plan()]

    assert "Walk" not in titles
    assert "Feed" in titles


# ---------------------------------------------------------------------------
# Edge case 11 — preferred_hour already in the past
# ---------------------------------------------------------------------------

def test_preferred_hour_in_past_does_not_rewind_clock():
    """
    When preferred_hour is earlier than the current time pointer,
    the scheduler starts the task immediately rather than going backward
    (which would overlap the previous entry).
    """
    owner = make_owner(start=8, end=20)
    pet = make_pet()
    # First task fills 08:00-09:00; second also prefers 08:00 (already past)
    pet.add_task(make_task("First",  duration=60, priority="high", preferred_hour=8))
    pet.add_task(make_task("Second", duration=30, priority="high", preferred_hour=8))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()
    times = {e.task.title: e.start_hour * 60 + e.start_minute for e in plan}

    assert times["First"] == 8 * 60
    assert times["Second"] >= 9 * 60   # must not rewind to 08:00


# ---------------------------------------------------------------------------
# Edge case 12 — all tasks already completed
# ---------------------------------------------------------------------------

def test_all_completed_tasks_yields_empty_plan():
    """build_plan() returns [] when every task is already marked done."""
    owner = make_owner()
    pet = make_pet()
    task = make_task("Walk")
    task.mark_done()
    pet.add_task(task)
    owner.add_pet(pet)

    assert Scheduler(owner).build_plan() == []


# ---------------------------------------------------------------------------
# Sorting correctness 13
# ---------------------------------------------------------------------------

def test_plan_entries_are_in_chronological_order():
    """
    Every ScheduledEntry in the plan must start at or after the previous one.

    Why this matters: the scheduler assigns start times by advancing a
    'current_minutes' pointer forward — it should never go backward.
    We convert (start_hour, start_minute) to total minutes so two entries
    that happen to span an hour boundary are still compared correctly.
    """
    owner = make_owner(start=8, end=20)
    pet = make_pet()
    pet.add_task(make_task("A", duration=20, priority="low",    preferred_hour=10))
    pet.add_task(make_task("B", duration=15, priority="high",   preferred_hour=8))
    pet.add_task(make_task("C", duration=30, priority="medium", preferred_hour=9))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()

    # Convert each entry to a single 'minutes since midnight' integer
    start_times = [e.start_hour * 60 + e.start_minute for e in plan]

    # Each start time must be >= the one before it
    assert start_times == sorted(start_times), (
        f"Plan is not chronological: {start_times}"
    )


# ---------------------------------------------------------------------------
# Recurrence logic 14
# ---------------------------------------------------------------------------

def test_daily_task_reappears_after_reset_day():
    """
    A 'daily' task that was marked complete should reappear in the next
    day's plan after Scheduler.reset_day() is called.

    How recurrence works in this system: tasks carry a 'frequency' label
    ("daily", "weekly", "as-needed") and a 'completed' flag.  The Scheduler
    only schedules tasks where completed=False.  Calling reset_day() sets
    every task's completed flag back to False, which is the equivalent of
    "starting a new day" — daily tasks become available again.
    """
    owner = make_owner()
    pet = make_pet()
    pet.add_task(make_task("Daily walk", duration=30, priority="high", frequency="daily"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner)

    # Day 1: schedule and complete the task
    scheduler.mark_complete("Daily walk")
    assert Scheduler(owner).build_plan() == []   # nothing pending

    # New day: reset reactivates the daily task
    scheduler.reset_day()
    plan = scheduler.build_plan()
    titles = [e.task.title for e in plan]

    assert "Daily walk" in titles, "Daily task should reappear after reset_day()"


# ---------------------------------------------------------------------------
# Conflict detection 15
# ---------------------------------------------------------------------------

def test_no_two_entries_share_the_same_start_time():
    """
    No two scheduled entries should start at the exact same minute.

    Why this matters: a conflict (two tasks at 09:00) would mean the owner
    is expected to do two things simultaneously — an impossible schedule.
    The greedy pointer advances by each task's duration before placing the
    next one, so overlaps should never occur.  This test makes that
    guarantee explicit and will catch any regression that resets the pointer
    incorrectly.
    """
    owner = make_owner(start=8, end=20)
    pet = make_pet()
    # Give several tasks the same preferred_hour to stress-test conflict avoidance
    for i in range(4):
        pet.add_task(make_task(f"Task {i}", duration=15, priority="medium", preferred_hour=9))
    owner.add_pet(pet)

    plan = Scheduler(owner).build_plan()

    start_times = [e.start_hour * 60 + e.start_minute for e in plan]

    # All start times must be unique
    assert len(start_times) == len(set(start_times)), (
        f"Duplicate start times detected: {start_times}"
    )


# ---------------------------------------------------------------------------
# Run directly:  python tests/test_pawpal.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_add_task_increases_pet_task_count,
        test_mark_complete_changes_task_status,
        test_high_priority_scheduled_before_low,
        test_get_all_tasks_spans_multiple_pets,
        test_get_available_minutes_correct,
        test_pet_with_no_tasks_returns_empty_plan,
        test_owner_with_no_pets_returns_empty_plan,
        test_oversized_task_is_skipped,
        test_species_filtered_task_excluded_for_wrong_species,
        test_mark_complete_removes_task_from_rebuilt_plan,
        test_preferred_hour_in_past_does_not_rewind_clock,
        test_all_completed_tasks_yields_empty_plan,
        test_plan_entries_are_in_chronological_order,
        test_daily_task_reappears_after_reset_day,
        test_no_two_entries_share_the_same_start_time,
    ]

    for t in tests:
        t()
        print(f"PASS  {t.__name__}")

    print(f"\nAll {len(tests)} tests passed.")
