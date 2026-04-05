import streamlit as st
from pawpal_system import CareTask, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session-state initialisation
#
# st.session_state works like a dictionary that Streamlit keeps alive for
# the entire browser session.  Every button click reruns this script from
# line 1, so we must guard each object with "if key not in st.session_state"
# to avoid recreating (and wiping) it on every rerun.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None          # set when the owner form is saved

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None      # created after owner exists

# ---------------------------------------------------------------------------
# Step 1 — Owner setup
# ---------------------------------------------------------------------------
st.subheader("1. Owner setup")

with st.form("owner_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        avail_start = st.number_input("Available from (hour)", min_value=0, max_value=23, value=8)
    with col3:
        avail_end = st.number_input("Available until (hour)", min_value=1, max_value=24, value=20)

    if st.form_submit_button("Save owner"):
        # Only create a new Owner if none exists yet, or if the name changed.
        # This preserves any pets/tasks already added during the session.
        if (st.session_state.owner is None
                or st.session_state.owner.name != owner_name):
            st.session_state.owner = Owner(
                name=owner_name,
                available_start=int(avail_start),
                available_end=int(avail_end),
            )
            st.session_state.scheduler = None   # reset scheduler on new owner
        else:
            # Update window without losing pets
            st.session_state.owner.available_start = int(avail_start)
            st.session_state.owner.available_end   = int(avail_end)
            st.session_state.scheduler = None

        st.success(f"Owner saved: {owner_name}  |  window {int(avail_start):02d}:00 – {int(avail_end):02d}:00")

if st.session_state.owner is None:
    st.info("Fill in the owner form above to get started.")
    st.stop()   # nothing else can work without an owner

owner: Owner = st.session_state.owner

st.divider()

# ---------------------------------------------------------------------------
# Step 2 — Add pets
# ---------------------------------------------------------------------------
st.subheader("2. Add pets")

with st.form("pet_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "other"])
    with col3:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=3)
    health_notes = st.text_input("Health notes (optional)", value="")

    if st.form_submit_button("Add pet"):
        existing_names = [p.name.lower() for p in owner.pets]
        if pet_name.lower() in existing_names:
            st.warning(f"{pet_name} is already registered.")
        else:
            owner.add_pet(Pet(
                name=pet_name,
                species=species,
                age=int(age),
                health_notes=health_notes,
            ))
            st.session_state.scheduler = None   # invalidate cached plan
            st.success(f"Added {pet_name} ({species}).")

if owner.pets:
    st.write("**Registered pets:**")
    for pet in owner.pets:
        st.write(f"  • {pet.summary()}")
else:
    st.info("No pets yet — add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Step 3 — Add tasks to a pet
# ---------------------------------------------------------------------------
st.subheader("3. Add tasks")

if not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        pet_choice = st.selectbox("Assign to pet", [p.name for p in owner.pets])
        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=30)
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

        col4, col5 = st.columns(2)
        with col4:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])
        with col5:
            preferred_hour = st.number_input(
                "Preferred hour (blank = any)", min_value=-1, max_value=23, value=-1,
                help="Set to -1 to leave unscheduled."
            )

        species_filter = st.selectbox(
            "Species filter (optional)", ["none", "dog", "cat", "other"]
        )

        if st.form_submit_button("Add task"):
            target_pet = next(p for p in owner.pets if p.name == pet_choice)
            target_pet.add_task(CareTask(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                frequency=frequency,
                preferred_hour=int(preferred_hour) if preferred_hour >= 0 else None,
                species_filter=None if species_filter == "none" else species_filter,
            ))
            st.session_state.scheduler = None   # invalidate cached plan
            st.success(f"Added '{task_title}' to {pet_choice}.")

    # Show all current tasks
    all_pairs = owner.get_all_tasks()
    if all_pairs:
        st.write("**Current tasks:**")
        rows = [
            {
                "Pet": pet.name,
                "Task": task.title,
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority,
                "Frequency": task.frequency,
                "Done": "✓" if task.completed else "",
            }
            for pet, task in all_pairs
        ]
        st.table(rows)

st.divider()

# ---------------------------------------------------------------------------
# Step 4 — Generate schedule
# ---------------------------------------------------------------------------
st.subheader("4. Today's schedule")

if st.button("Generate schedule"):
    if not owner.pets or not owner.get_all_tasks():
        st.warning("Add at least one pet and one task first.")
    else:
        # Build a fresh Scheduler and cache it
        st.session_state.scheduler = Scheduler(owner)
        plan = st.session_state.scheduler.build_plan()

        if not plan:
            st.error("No tasks could fit within the availability window.")
        else:
            st.success(f"{len(plan)} task(s) scheduled for {owner.name}.")
            rows = [
                {
                    "Time": entry.start_time_str(),
                    "Pet": entry.pet.name,
                    "Task": entry.task.title,
                    "Duration (min)": entry.task.duration_minutes,
                    "Priority": entry.task.priority.upper(),
                    "Frequency": entry.task.frequency,
                    "Reason": entry.reason,
                }
                for entry in plan
            ]
            st.table(rows)

            total = sum(e.task.duration_minutes for e in plan)
            st.caption(f"Total scheduled time: {total} min")
