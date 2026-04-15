"""Tests for AI explanation fallback and Gemini integration paths."""

from ai_explainer import answer_followup_question, explain_schedule
from knowledge_base import RetrievedFact
from pawpal_system import Pet, PetOwner, PlanItem, Task


class _FakeClient:
    def __init__(self, text: str):
        self._text = text

    def generate_content(self, _prompt: str):
        class _Response:
            def __init__(self, text: str):
                self.text = text

        return _Response(self._text)


class _CapturePromptClient:
    def __init__(self, text: str = "ok"):
        self._text = text
        self.prompt = ""

    def generate_content(self, prompt: str):
        self.prompt = prompt

        class _Response:
            def __init__(self, text: str):
                self.text = text

        return _Response(self._text)


def _sample_inputs():
    task = Task("Morning walk", "walk", 30, "high")
    plan = [PlanItem(task=task, scheduled_time=540, duration_minutes=30, reason="Scheduled first")]
    facts = {
        "Morning walk": [
            RetrievedFact(
                text="Dogs usually need 30 to 60 minutes of exercise each day.",
                score=0.87,
                topic="exercise",
            )
        ]
    }
    pet = Pet("Mochi", "dog")
    owner = PetOwner("Jordan", availability=(480, 1320))
    return plan, facts, pet, owner


def test_explain_schedule_uses_fallback_without_key(monkeypatch) -> None:
    plan, facts, pet, owner = _sample_inputs()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    explanation = explain_schedule(
        plan_items=plan,
        retrieved_facts=facts,
        pet=pet,
        owner=owner,
        api_key="",
    )

    assert "Fallback Mode" in explanation
    assert "Morning walk" in explanation


def test_explain_schedule_uses_client_when_available() -> None:
    plan, facts, pet, owner = _sample_inputs()

    explanation = explain_schedule(
        plan_items=plan,
        retrieved_facts=facts,
        pet=pet,
        owner=owner,
        client=_FakeClient("Gemini explanation output"),
    )

    assert explanation == "Gemini explanation output"


def test_followup_answer_uses_fallback_when_client_unavailable(monkeypatch) -> None:
    plan, facts, pet, owner = _sample_inputs()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    answer = answer_followup_question(
        question="Why is Morning walk first?",
        plan_items=plan,
        retrieved_facts=facts,
        pet=pet,
        owner=owner,
        api_key="",
    )

    assert "Morning walk" in answer
    assert "Retrieved context" in answer


def test_explain_schedule_prompt_allows_general_guidance_when_no_retrieval() -> None:
    plan, _facts, pet, owner = _sample_inputs()
    client = _CapturePromptClient("ok")

    explain_schedule(
        plan_items=plan,
        retrieved_facts={"Morning walk": []},
        pet=pet,
        owner=owner,
        client=client,
    )

    assert "No retrieval evidence was found for this run" in client.prompt
    assert "general guidance" in client.prompt


def test_followup_prompt_allows_general_guidance_when_no_retrieval() -> None:
    plan, _facts, pet, owner = _sample_inputs()
    client = _CapturePromptClient("ok")

    answer_followup_question(
        question="Why is Morning walk first?",
        plan_items=plan,
        retrieved_facts={"Morning walk": []},
        pet=pet,
        owner=owner,
        client=client,
    )

    assert "No retrieved evidence is available for this schedule" in client.prompt
    assert "general guidance" in client.prompt
