"""
pawpal_system.py
Logic layer for PawPal+ — all backend classes live here.

Architecture:
  CareTask  — a single activity with description, time, frequency, and status
  Pet       — stores pet details and owns a list of CareTasks
  Owner     — manages multiple pets; aggregates all tasks across them
  Scheduler — the "brain": asks Owner for tasks, organizes, and manages the plan
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# CareTask — a single care activity
# ---------------------------------------------------------------------------

@dataclass
class CareTask:
    """
    Represents one care activity for a pet.

    Attributes
    ----------
    title           : short name, e.g. "Morning walk"
    duration_minutes: how long the activity takes
    priority        : "low", "medium", or "high"
    frequency       : how often it recurs — "daily", "weekly", or "as-needed"
    preferred_hour  : optional preferred start hour (0-23)
    species_filter  : if set, only schedule for pets of this species
    completed       : True once the task has been marked done for the day
    """
    title: str
    duration_minutes: int
    priority: str                       # "low" | "medium" | "high"
    frequency: str = "daily"            # "daily" | "weekly" | "as-needed"
    preferred_hour: int | None = None   # 0-23
    species_filter: str | None = None   # e.g. "cat", "dog"
    completed: bool = False

    def priority_value(self) -> int:
        """Return a sortable integer for priority (higher = more urgent)."""
        return {"low": 1, "medium": 2, "high": 3}.get(self.priority, 0)

    def mark_done(self) -> None:
        """Mark this task as completed for the day."""
        self.completed = True

    def reset(self) -> None:
        """Reset completion status (e.g. at the start of a new day)."""
        self.completed = False


# ---------------------------------------------------------------------------
# Pet — stores pet details and owns its tasks
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """
    Represents a pet and the care tasks associated with it.

    Attributes
    ----------
    name        : pet's name
    species     : "dog", "cat", or "other"
    age         : age in years
    health_notes: free-text notes (allergies, medical conditions, etc.)
    tasks       : list of CareTasks that belong to this pet
    """
    name: str
    species: str
    age: int
    health_notes: str = ""
    tasks: list[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """Remove the first task matching title (case-insensitive); return True if found."""
        for i, t in enumerate(self.tasks):
            if t.title.lower() == title.lower():
                self.tasks.pop(i)
                return True
        return False

    def get_pending_tasks(self) -> list[CareTask]:
        """Return tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.completed]

    def summary(self) -> str:
        """Return a short human-readable description of the pet."""
        pending = len(self.get_pending_tasks())
        return (
            f"{self.name} ({self.species}, {self.age}yr) — "
            f"{pending} pending task(s)"
            + (f" | Notes: {self.health_notes}" if self.health_notes else "")
        )


# ---------------------------------------------------------------------------
# Owner — manages multiple pets and aggregates their tasks
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """
    Represents the pet owner and their daily availability window.

    The Owner is the entry point for the Scheduler: it can return all tasks
    across every pet via get_all_tasks().
    """
    name: str
    available_start: int    # hour 0-23 (e.g. 8 = 8 AM)
    available_end: int      # hour 0-23 (e.g. 20 = 8 PM)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> bool:
        """Remove the first pet matching name (case-insensitive); return True if found."""
        for i, p in enumerate(self.pets):
            if p.name.lower() == name.lower():
                self.pets.pop(i)
                return True
        return False

    def get_available_minutes(self) -> int:
        """Return the total minutes available within the owner's window (0 if window is invalid)."""
        return max(0, (self.available_end - self.available_start) * 60)

    def get_all_tasks(self) -> list[tuple[Pet, CareTask]]:
        """Return all (pet, task) pairs across every owned pet."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def get_all_pending_tasks(self) -> list[tuple[Pet, CareTask]]:
        """Return only incomplete tasks across all pets."""
        return [
            (pet, task)
            for pet in self.pets
            for task in pet.get_pending_tasks()
        ]


# ---------------------------------------------------------------------------
# ScheduledEntry — one typed slot in the daily plan
# ---------------------------------------------------------------------------

@dataclass
class ScheduledEntry:
    """One time-slot in the generated daily plan."""
    pet: Pet
    task: CareTask
    start_hour: int
    start_minute: int
    reason: str

    def start_time_str(self) -> str:
        """Return the start time formatted as HH:MM."""
        return f"{self.start_hour:02d}:{self.start_minute:02d}"


# ---------------------------------------------------------------------------
# Scheduler — the "brain" that organizes and manages tasks
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Retrieves tasks from Owner.get_all_pending_tasks(), applies scheduling
    rules, and produces an ordered daily plan.

    How it talks to Owner
    ---------------------
    owner.get_all_pending_tasks() → list[(Pet, CareTask)]
      The Scheduler never reaches into owner.pets directly; it always uses
      this method so the Owner controls what data is exposed.

    Scheduling rules (in order)
    ---------------------------
    1. Skip tasks already marked completed.
    2. Skip tasks whose species_filter does not match the pet's species.
    3. Sort remaining tasks: high priority first, then preferred_hour
       (tasks with a preferred hour are placed at that hour if possible).
    4. Assign start times greedily from available_start.
    5. Stop when no more tasks fit inside the available window.
    """

    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self._plan: list[ScheduledEntry] | None = None  # cache

    def build_plan(self) -> list[ScheduledEntry]:
        """Build (or return cached) the daily plan."""
        if self._plan is not None:
            return self._plan

        # Step 1: ask Owner for all pending (pet, task) pairs
        candidates = self.owner.get_all_pending_tasks()

        # Step 2: filter tasks whose species_filter mismatches
        candidates = [
            (pet, task) for pet, task in candidates
            if task.species_filter is None
            or task.species_filter.lower() == pet.species.lower()
        ]

        # Step 3: sort — high priority first; within same priority,
        #         tasks with a preferred_hour come before those without
        candidates.sort(
            key=lambda pt: (
                -pt[1].priority_value(),
                pt[1].preferred_hour if pt[1].preferred_hour is not None else 99,
            )
        )

        # Step 4: assign start times greedily
        plan: list[ScheduledEntry] = []
        current_minutes = self.owner.available_start * 60
        end_minutes = self.owner.available_end * 60

        for pet, task in candidates:
            if current_minutes + task.duration_minutes > end_minutes:
                continue   # task too long for remaining time; try a shorter one

            # Honour preferred_hour: if preferred start hasn't passed yet,
            # jump forward to it (never backwards)
            if task.preferred_hour is not None:
                preferred_start = task.preferred_hour * 60
                if preferred_start > current_minutes:
                    current_minutes = preferred_start

            if current_minutes + task.duration_minutes > end_minutes:
                continue   # preferred_hour pushed it past the window; skip

            entry = ScheduledEntry(
                pet=pet,
                task=task,
                start_hour=current_minutes // 60,
                start_minute=current_minutes % 60,
                reason=(
                    f"Priority '{task.priority}' task for {pet.name}; "
                    f"fits within availability window."
                ),
            )
            plan.append(entry)
            current_minutes += task.duration_minutes

        self._plan = plan
        return self._plan

    def mark_complete(self, task_title: str) -> bool:
        """Find task by title across all pets, mark it done, and invalidate the cache; return True if found."""
        for _, task in self.owner.get_all_tasks():
            if task.title.lower() == task_title.lower():
                task.mark_done()
                self._plan = None   # invalidate cache
                return True
        return False

    def reset_day(self) -> None:
        """Reset all tasks to incomplete and clear the cached plan."""
        for _, task in self.owner.get_all_tasks():
            task.reset()
        self._plan = None

    def explain_plan(self) -> str:
        """Return a human-readable summary of the daily plan, building it first if needed."""
        plan = self.build_plan()
        if not plan:
            return f"No tasks scheduled for {self.owner.name} today."

        lines = [f"Daily plan for {self.owner.name}:\n"]
        for entry in plan:
            lines.append(
                f"  {entry.start_time_str()}  [{entry.task.priority.upper()}]  "
                f"{entry.task.title} ({entry.task.duration_minutes} min) "
                f"— {entry.pet.name}  |  {entry.reason}"
            )

        total = sum(e.task.duration_minutes for e in plan)
        lines.append(f"\nTotal scheduled: {total} min across {len(plan)} task(s).")
        return "\n".join(lines)
