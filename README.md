# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
python -m streamlit run app.py
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

---

## Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest tests/test_pawpal.py -v
```

Or without pytest installed:

```bash
python tests/test_pawpal.py
```

### What the tests cover

15 tests across two categories:

**Happy paths** — the system doing what it should:
- Adding a task increases the pet's task count
- `mark_complete()` flips a task's status to done
- High-priority tasks are scheduled before low-priority ones
- `get_all_tasks()` correctly aggregates tasks across multiple pets
- `get_available_minutes()` returns the right window size

**Edge cases** — where things could quietly break:
- A pet with no tasks returns an empty plan (no crash)
- An owner with no pets returns an empty plan (no crash)
- A task too long to fit is skipped — shorter tasks still schedule
- A species-filtered task (e.g. dog-only) is excluded from a cat's plan
- `mark_complete()` busts the plan cache so the rebuilt plan is accurate
- A `preferred_hour` already in the past doesn't rewind the clock
- All tasks already completed returns an empty plan
- Plan entries are always in chronological order (no time travel)
- A daily task reappears after `reset_day()` (recurrence logic)
- No two entries share the same start time (no double-booking)

### Confidence level

⭐⭐⭐⭐ 4 / 5

The core scheduling logic — priority sorting, species filtering, time-window fitting, and cache invalidation — is fully tested and all 15 tests pass. One star held back because there is no test for multi-day recurrence with real dates, and the `preferred_hour` behavior when multiple tasks compete for the same slot could use more coverage.
