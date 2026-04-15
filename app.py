import os

import streamlit as st
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - defensive fallback for missing optional dependency
    load_dotenv = None

from ai_explainer import answer_followup_question, explain_schedule
from knowledge_base import SemanticRetriever
from logging_config import setup_logging
from pawpal_system import Task, Pet, PetOwner, Scheduler

# Load local environment variables (e.g., GEMINI_API_KEY) before app logic runs.
if load_dotenv is not None:
    load_dotenv()

setup_logging()

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("📋 Setup Your Pet & Owner")
setup_col1, setup_col2, setup_col3 = st.columns(3)
with setup_col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with setup_col2:
    pet_name = st.text_input("Pet name", value="Mochi")
with setup_col3:
    species = st.selectbox("Species", ["🐕 dog", "🐱 cat", "🦜 other"])

st.divider()

st.subheader("➕ Add Tasks")
st.caption("Build your task list. Tasks are sorted chronologically and checked for conflicts.")

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()
if "retriever" not in st.session_state:
    st.session_state.retriever = SemanticRetriever()
if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None
if "generated_pet" not in st.session_state:
    st.session_state.generated_pet = None
if "generated_owner" not in st.session_state:
    st.session_state.generated_owner = None
if "retrieved_facts" not in st.session_state:
    st.session_state.retrieved_facts = {}
if "schedule_explanation" not in st.session_state:
    st.session_state.schedule_explanation = ""
if "explanation_mode" not in st.session_state:
    st.session_state.explanation_mode = "unknown"
if "followup_history" not in st.session_state:
    st.session_state.followup_history = []

# Task input form with better layout
input_col1, input_col2, input_col3, input_col4 = st.columns(4)
with input_col1:
    task_title = st.text_input("Task title", value="Morning walk", placeholder="e.g., Morning walk")
with input_col2:
    duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
with input_col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with input_col4:
    task_type = st.selectbox("Type", ["walk", "feed", "groom", "play", "other"], key="task_type_select")

task_notes = st.text_area("Notes (optional)", value="", height=80)

if st.button("➕ Add Task", use_container_width=True):
    task = Task(
        title=task_title,
        task_type=task_type,
        duration_minutes=int(duration),
        priority=priority,
        notes=task_notes
    )
    if st.session_state.scheduler.add_task(task):
        st.success(f"✅ Added task: **{task.title}**")
    else:
        st.error("❌ Invalid task. Please check the inputs.")

if st.session_state.scheduler.tasks:
    st.subheader("📊 Task Overview")
    
    # Task statistics
    sorted_tasks = st.session_state.scheduler.sort_by_time()
    total_duration = sum(t.duration_minutes for t in sorted_tasks)
    high_priority = len([t for t in sorted_tasks if t.priority == "high"])
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    with stat_col1:
        st.metric("📝 Total Tasks", len(sorted_tasks))
    with stat_col2:
        st.metric("⏱️ Total Duration", f"{total_duration} min")
    with stat_col3:
        st.metric("🔴 High Priority", high_priority)
    
    # Task list as interactive dataframe
    st.markdown("**Task List** (sorted by start time)")
    task_display_data = [
        {
            "Title": t.title,
            "Type": t.task_type,
            "Duration (min)": t.duration_minutes,
            "Priority": t.priority.upper(),
            "Start Time": f"{t.start_time // 60:02d}:{t.start_time % 60:02d}" if t.start_time is not None else "Not set",
            "Notes": t.notes if t.notes else "—"
        }
        for t in sorted_tasks
    ]
    st.dataframe(task_display_data, use_container_width=True, hide_index=True)
    
    # Detect and display any scheduling conflicts
    conflicts = st.session_state.scheduler.detect_scheduling_conflicts()
    if conflicts:
        with st.warning("**⚠️  Scheduling Conflicts Detected**", icon="⚠️"):
            for conflict in conflicts:
                st.caption(conflict)
    else:
        st.success("✅ No conflicts detected in current task list", icon="✅")
else:
    st.info("📭 No tasks yet. Add your first task above to get started!")

st.divider()

st.subheader("📅 Build Schedule")
st.caption("Generate an optimized daily plan for your pet based on tasks and availability.")

if st.button("🚀 Generate Schedule", use_container_width=True):
    if not st.session_state.scheduler.tasks:
        st.error("❌ No tasks added. Please add at least one task above.")
    else:
        scheduler = st.session_state.scheduler

        # Create and add pet
        clean_species = species.split(" ", 1)[-1].strip().lower()
        pet = Pet(name=pet_name, species=clean_species)
        scheduler.set_pet(pet)

        # Set owner and availability (default: 8am to 10pm = 480 to 1320 minutes)
        owner = PetOwner(name=owner_name, availability=(480, 1320))
        scheduler.set_owner(owner)
        
        # Check for conflicts before generating plan
        pre_plan_conflicts = scheduler.detect_scheduling_conflicts()
        if pre_plan_conflicts:
            with st.warning("**⚠️  Pre-scheduling Conflicts**", icon="⚠️"):
                for conflict in pre_plan_conflicts:
                    st.caption(conflict)
        
        # Generate plan
        plan = scheduler.generate_plan()
        
        if plan:
            retrieved_facts = st.session_state.retriever.retrieve_for_plan(plan, pet=pet)
            explanation = explain_schedule(
                plan_items=plan,
                retrieved_facts=retrieved_facts,
                pet=pet,
                owner=owner,
                conversation_history=None,
            )

            st.session_state.generated_plan = plan
            st.session_state.generated_pet = pet
            st.session_state.generated_owner = owner
            st.session_state.retrieved_facts = retrieved_facts
            st.session_state.schedule_explanation = explanation
            if explanation.lstrip().startswith("### Schedule Explanation (Fallback Mode)"):
                st.session_state.explanation_mode = "fallback"
            else:
                st.session_state.explanation_mode = "gemini"
            st.session_state.followup_history = []

            st.success(f"✅ Schedule generated for {pet_name}!", icon="✅")
            
            # Schedule header
            schedule_col1, schedule_col2 = st.columns([2, 1])
            with schedule_col1:
                st.markdown(f"### 🐾 Daily Plan for {pet_name}")
            with schedule_col2:
                st.markdown(f"**Owner:** {owner_name}\n**Time:** 8:00 AM - 10:00 PM")
            
            # Separate scheduled and unscheduled items
            scheduled_items = [item for item in plan if item.scheduled_time >= 0]
            unscheduled_items = [item for item in plan if item.scheduled_time < 0]
            
            # Schedule statistics
            total_scheduled_time = sum(item.duration_minutes for item in scheduled_items)
            available_time = 1320 - 480  # 10 PM - 8 AM
            utilization_pct = (total_scheduled_time / available_time * 100) if available_time > 0 else 0
            
            sched_col1, sched_col2, sched_col3 = st.columns(3)
            with sched_col1:
                st.metric("✓ Scheduled Tasks", len(scheduled_items))
            with sched_col2:
                st.metric("⏱️ Total Time", f"{total_scheduled_time} min")
            with sched_col3:
                st.metric("📊 Utilization", f"{utilization_pct:.0f}%")
            
            st.divider()
            
            # Display scheduled items in professional cards
            if scheduled_items:
                st.markdown("#### ✅ Scheduled Tasks")
                for idx, item in enumerate(scheduled_items, 1):
                    hours = item.scheduled_time // 60
                    minutes = item.scheduled_time % 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                    
                    # Priority styling
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                    priority_badge = priority_emoji.get(item.task.priority, "")
                    
                    # Create a card-like display
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(f"### {time_str}")
                    with col2:
                        st.markdown(
                            f"**{item.task.title}** {priority_badge} ({item.duration_minutes} min)\n"
                            f"*{item.task.task_type.title()}* | {item.task.priority.upper()}\n"
                            f"> 💭 {item.reason}"
                        )
                    st.divider()
            else:
                st.warning("⚠️  No tasks could be scheduled within the available time window.")
            
            # Display unscheduled items
            if unscheduled_items:
                st.markdown(f"#### ❌ Could Not Schedule ({len(unscheduled_items)} tasks)")
                for item in unscheduled_items:
                    with st.expander(f"📌 {item.task.title}", expanded=False):
                        st.markdown(f"**Reason:** {item.reason}")
                        st.markdown(f"**Duration:** {item.duration_minutes} minutes")
                        st.markdown(f"**Priority:** {item.task.priority.upper()}")
                        if item.task.notes:
                            st.markdown(f"**Notes:** {item.task.notes}")
        else:
            st.error("❌ Could not generate a schedule. Please verify your inputs and try again.")

if st.session_state.generated_plan:
    st.divider()
    st.subheader("🤖 AI Explanation (RAG)")
    st.caption("This explanation is grounded in retrieved pet-care facts for each task.")

    st.markdown("#### AI Health")
    health_col1, health_col2 = st.columns(2)
    with health_col1:
        engine_value = "Gemini Active" if st.session_state.explanation_mode == "gemini" else "Fallback Mode"
        st.metric("Engine", engine_value)
    with health_col2:
        key_value = "Configured" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "Missing"
        st.metric("Gemini API Key", key_value)

    if st.session_state.explanation_mode == "fallback":
        st.warning(
            "Gemini output was unavailable for this run, so the app used local fallback reasoning.",
            icon="⚠️",
        )
    else:
        st.success("Gemini responded successfully for this schedule.", icon="✅")

    st.markdown(st.session_state.schedule_explanation)

    with st.expander("View retrieved evidence", expanded=False):
        for task_title, facts in st.session_state.retrieved_facts.items():
            st.markdown(f"**{task_title}**")
            if not facts:
                st.caption("No specific guideline retrieved for this task.")
                continue
            for fact in facts:
                st.caption(f"- ({fact.score:.2f}) {fact.text}")

    st.subheader("💬 Ask Follow-up Questions")
    st.caption("Questions are remembered for this schedule in the current app session.")

    for message in st.session_state.followup_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    followup_question = st.chat_input("Ask about timing, priorities, or why a task was placed where it is")
    if followup_question:
        st.session_state.followup_history.append({"role": "user", "content": followup_question})
        with st.chat_message("user"):
            st.markdown(followup_question)

        answer = answer_followup_question(
            question=followup_question,
            plan_items=st.session_state.generated_plan,
            retrieved_facts=st.session_state.retrieved_facts,
            pet=st.session_state.generated_pet,
            owner=st.session_state.generated_owner,
            conversation_history=st.session_state.followup_history,
        )
        st.session_state.followup_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
