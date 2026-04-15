"""Gemini-backed explanation service for schedule reasoning and follow-up Q&A."""

from __future__ import annotations

from dataclasses import asdict
import json
import logging
import os
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

from knowledge_base import RetrievedFact

if TYPE_CHECKING:
    from pawpal_system import Pet, PetOwner, PlanItem


logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gemini-2.5-flash"


def explain_schedule(
    plan_items: Sequence["PlanItem"],
    retrieved_facts: Dict[str, List[RetrievedFact]],
    pet: "Pet",
    owner: "PetOwner",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    client: Optional[object] = None,
) -> str:
    """Explain why the schedule was generated using retrieved context."""
    context_payload = _build_context_payload(plan_items, retrieved_facts, pet, owner)
    has_retrieved_data = _has_any_retrieved_data(retrieved_facts)
    logger.info("RAG context for explanation: %s", json.dumps(context_payload)[:1200])

    guidance_mode = (
        "Ground explanations in retrieved facts whenever available. "
        "If a specific task has no retrieved facts, use cautious general pet-care intuition and label it as general guidance."
        if has_retrieved_data
        else "No retrieval evidence was found for this run. Use general pet-care intuition to provide a practical explanation, "
        "and clearly label recommendations as general guidance rather than retrieved evidence."
    )

    content = (
        "You are PawPal+, an assistant that explains pet care schedules. "
        f"{guidance_mode}\n\n"
        "Produce:\n"
        "1) A short overview of scheduling strategy\n"
        "2) Bullet explanations per scheduled task\n"
        "3) A note for unscheduled tasks\n"
        "4) A brief safety reminder to verify with a veterinarian for medical concerns\n\n"
        f"Data:\n{json.dumps(context_payload, indent=2)}"
    )

    messages = _build_messages(conversation_history, user_content=content)
    response = _call_gemini(messages=messages, model=model, api_key=api_key, client=client)

    if response:
        logger.info("Gemini explanation generated (%d chars)", len(response))
        return response

    logger.warning("Using fallback explanation because Gemini response was unavailable")
    return _fallback_schedule_explanation(plan_items, retrieved_facts)


def answer_followup_question(
    question: str,
    plan_items: Sequence["PlanItem"],
    retrieved_facts: Dict[str, List[RetrievedFact]],
    pet: "Pet",
    owner: "PetOwner",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    client: Optional[object] = None,
) -> str:
    """Answer follow-up questions using the same RAG context and chat history."""
    question = question.strip()
    if not question:
        return "Please ask a question about the schedule."

    context_payload = _build_context_payload(plan_items, retrieved_facts, pet, owner)
    has_retrieved_data = _has_any_retrieved_data(retrieved_facts)
    grounding_instruction = (
        "Ground the answer in retrieved facts and task timing. If evidence is missing for part of the question, "
        "use cautious general pet-care intuition and label it as general guidance."
        if has_retrieved_data
        else "No retrieved evidence is available for this schedule. Use general pet-care intuition and task timing, "
        "and clearly label the answer as general guidance."
    )
    user_content = (
        "Answer the user question about the current schedule. "
        f"{grounding_instruction}\n\n"
        f"Question: {question}\n\n"
        f"Data: {json.dumps(context_payload, indent=2)}"
    )

    messages = _build_messages(conversation_history, user_content=user_content)
    response = _call_gemini(messages=messages, model=model, api_key=api_key, client=client)

    if response:
        logger.info("Gemini follow-up answer generated (%d chars)", len(response))
        return response

    logger.warning("Using fallback follow-up answer because Gemini response was unavailable")
    return _fallback_followup_answer(question, plan_items, retrieved_facts)


def _build_context_payload(
    plan_items: Sequence["PlanItem"],
    retrieved_facts: Dict[str, List[RetrievedFact]],
    pet: "Pet",
    owner: "PetOwner",
) -> Dict[str, object]:
    scheduled = []
    unscheduled = []

    for item in plan_items:
        payload = {
            "task_title": item.task.title,
            "task_type": item.task.task_type,
            "priority": item.task.priority,
            "time": _format_time(item.scheduled_time) if item.scheduled_time >= 0 else "unscheduled",
            "duration_minutes": item.duration_minutes,
            "scheduler_reason": item.reason,
            "retrieved_facts": [asdict(fact) for fact in retrieved_facts.get(item.task.title, [])],
        }
        if item.scheduled_time >= 0:
            scheduled.append(payload)
        else:
            unscheduled.append(payload)

    return {
        "pet": {
            "name": pet.name,
            "species": pet.species,
            "preferences": pet.get_preferences(),
        },
        "owner": {
            "name": owner.name,
            "availability": owner.availability,
            "preferences": owner.get_preferences(),
        },
        "scheduled_tasks": scheduled,
        "unscheduled_tasks": unscheduled,
    }


def _has_any_retrieved_data(retrieved_facts: Dict[str, List[RetrievedFact]]) -> bool:
    return any(bool(facts) for facts in retrieved_facts.values())


def _build_messages(
    conversation_history: Optional[List[Dict[str, str]]],
    user_content: str,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if conversation_history:
        for item in conversation_history[-8:]:
            role = item.get("role", "user")
            if role in ("user", "assistant") and item.get("content"):
                messages.append({"role": role, "content": item["content"]})

    messages.append({"role": "user", "content": user_content})
    return messages


def _call_gemini(
    messages: List[Dict[str, str]],
    model: str,
    api_key: Optional[str] = None,
    client: Optional[object] = None,
) -> Optional[str]:
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key and client is None:
        logger.warning("GEMINI_API_KEY/GOOGLE_API_KEY was not set; Gemini call skipped")
        return None

    gemini_client = client
    if gemini_client is None:
        try:
            import google.generativeai as genai

            genai.configure(api_key=key)
            gemini_client = genai.GenerativeModel(model)
        except Exception as exc:
            logger.exception("Failed to initialize Gemini client: %s", exc)
            return None

    try:
        prompt = _messages_to_prompt(messages)
        if hasattr(gemini_client, "generate_content"):
            response = gemini_client.generate_content(prompt)
            return _extract_text_from_response(response)

        # Compatibility path for clients that expose a .models.generate_content API.
        if hasattr(gemini_client, "models") and hasattr(gemini_client.models, "generate_content"):
            response = gemini_client.models.generate_content(model=model, contents=prompt)
            return _extract_text_from_response(response)

        logger.warning("Gemini client did not expose a supported generate method")
        return None
    except Exception as exc:
        logger.exception("Gemini API call failed: %s", exc)
        return None


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for message in messages:
        role = message.get("role", "user").upper()
        content = message.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def _extract_text_from_response(response: object) -> Optional[str]:
    direct_text = getattr(response, "text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return None

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        for part in parts:
            text = getattr(part, "text", "")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _format_time(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _fallback_schedule_explanation(
    plan_items: Sequence["PlanItem"],
    retrieved_facts: Dict[str, List[RetrievedFact]],
) -> str:
    lines = [
        "### Schedule Explanation (Fallback Mode)",
        "Gemini is currently unavailable, so this explanation is generated locally.",
        "",
    ]

    for item in plan_items:
        facts = retrieved_facts.get(item.task.title, [])
        if item.scheduled_time >= 0:
            line = f"- {_format_time(item.scheduled_time)}: {item.task.title} ({item.task.priority} priority). {item.reason}"
        else:
            line = f"- Unscheduled: {item.task.title}. {item.reason}"

        if facts:
            line += f" Evidence: {facts[0].text}"
        else:
            line += " No specific guideline was retrieved for this task."
        lines.append(line)

    lines.append("\nPlease verify medical decisions with your veterinarian.")
    return "\n".join(lines)


def _fallback_followup_answer(
    question: str,
    plan_items: Sequence["PlanItem"],
    retrieved_facts: Dict[str, List[RetrievedFact]],
) -> str:
    lowered = question.lower()
    for item in plan_items:
        if item.task.title.lower() in lowered:
            facts = retrieved_facts.get(item.task.title, [])
            if item.scheduled_time >= 0:
                timing = _format_time(item.scheduled_time)
                if facts:
                    return (
                        f"{item.task.title} is scheduled at {timing}. "
                        f"The scheduler reason is: {item.reason}. "
                        f"Retrieved context: {facts[0].text}"
                    )
                return (
                    f"{item.task.title} is scheduled at {timing}. "
                    f"The scheduler reason is: {item.reason}. "
                    "No specific guideline was retrieved for this task."
                )
            return (
                f"{item.task.title} is currently unscheduled. "
                f"Reason: {item.reason}."
            )

    return (
        "I could not find enough retrieved context tied to that question. "
        "Try mentioning a specific task title from the schedule."
    )
