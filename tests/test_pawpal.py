"""
tests/test_pawpal.py
Simple unit tests for PawPal+ core logic.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import CareTask, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Test 1 — Task completion
# ---------------------------------------------------------------------------

def test_mark_complete_changes_task_status():
    """
    Calling Scheduler.mark_complete() should flip the matching task's
    completed flag from False to True.
    """
    owner = Owner(name="Alex", available_start=8, available_end=20)
    pet = Pet(name="Buddy", species="dog", age=2)
    pet.add_task(CareTask(title="Morning walk", duration_minutes=30, priority="high"))
    owner.add_pet(pet)

    scheduler = Scheduler(owner)

    # Task should start as not completed
    assert pet.tasks[0].completed is False

    result = scheduler.mark_complete("Morning walk")

    assert result is True, "mark_complete() should return True when the task is found"
    assert pet.tasks[0].completed is True, "Task should be marked completed"


# ---------------------------------------------------------------------------
# Test 2 — Task addition
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """
    Calling Pet.add_task() should increase the pet's task list length by one
    for each task added.
    """
    pet = Pet(name="Whiskers", species="cat", age=4)

    assert len(pet.tasks) == 0

    pet.add_task(CareTask(title="Clean litter box", duration_minutes=10, priority="high"))
    assert len(pet.tasks) == 1

    pet.add_task(CareTask(title="Brush coat", duration_minutes=15, priority="low"))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Run directly with: python tests/test_pawpal.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_mark_complete_changes_task_status()
    print("PASS  test_mark_complete_changes_task_status")

    test_add_task_increases_pet_task_count()
    print("PASS  test_add_task_increases_pet_task_count")

    print("\nAll tests passed.")
