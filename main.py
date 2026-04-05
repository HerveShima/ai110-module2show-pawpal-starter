"""
main.py
Temporary testing ground — verifies pawpal_system logic in the terminal.
"""

from pawpal_system import CareTask, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# 1. Create the owner
# ---------------------------------------------------------------------------
owner = Owner(name="Jordan", available_start=8, available_end=20)

# ---------------------------------------------------------------------------
# 2. Create two pets
# ---------------------------------------------------------------------------
mochi = Pet(name="Mochi", species="dog", age=3, health_notes="Allergic to chicken")
luna  = Pet(name="Luna",  species="cat", age=5)

owner.add_pet(mochi)
owner.add_pet(luna)

# ---------------------------------------------------------------------------
# 3. Add tasks to each pet (mix of priorities, times, and species filters)
# ---------------------------------------------------------------------------
mochi.add_task(CareTask(
    title="Morning walk",
    duration_minutes=30,
    priority="high",
    frequency="daily",
    preferred_hour=8,
))
mochi.add_task(CareTask(
    title="Flea & tick medicine",
    duration_minutes=5,
    priority="medium",
    frequency="weekly",
    preferred_hour=9,
    species_filter="dog",
))
mochi.add_task(CareTask(
    title="Evening walk",
    duration_minutes=20,
    priority="high",
    frequency="daily",
    preferred_hour=18,
))

luna.add_task(CareTask(
    title="Clean litter box",
    duration_minutes=10,
    priority="high",
    frequency="daily",
    preferred_hour=8,
    species_filter="cat",
))
luna.add_task(CareTask(
    title="Brush coat",
    duration_minutes=15,
    priority="low",
    frequency="weekly",
))
luna.add_task(CareTask(
    title="Playtime",
    duration_minutes=20,
    priority="medium",
    frequency="daily",
    preferred_hour=17,
))

# ---------------------------------------------------------------------------
# 4. Build and print "Today's Schedule"
# ---------------------------------------------------------------------------
scheduler = Scheduler(owner)
plan = scheduler.build_plan()

# ── Header ──────────────────────────────────────────────────────────────────
print("=" * 60)
print(f"  TODAY'S SCHEDULE  —  Owner: {owner.name}")
print(f"  Window: {owner.available_start:02d}:00 – {owner.available_end:02d}:00"
      f"  ({owner.get_available_minutes()} min available)")
print("=" * 60)

if not plan:
    print("  No tasks could be scheduled today.")
else:
    for entry in plan:
        priority_tag = f"[{entry.task.priority.upper():6}]"
        freq_tag     = f"({entry.task.frequency})"
        print(
            f"  {entry.start_time_str()}  {priority_tag}  "
            f"{entry.task.title:<25} {entry.task.duration_minutes:>3} min  "
            f"— {entry.pet.name:<6}  {freq_tag}"
        )

# ── Footer summary ───────────────────────────────────────────────────────────
total_min  = sum(e.task.duration_minutes for e in plan)
total_hr   = total_min // 60
leftover   = total_min % 60
print("-" * 60)
print(f"  {len(plan)} task(s) scheduled  |  "
      f"Total time: {total_hr}h {leftover:02d}m")
print("=" * 60)

# ── Per-pet summaries ────────────────────────────────────────────────────────
print()
print("Pet summaries:")
for pet in owner.pets:
    print(f"  • {pet.summary()}")
