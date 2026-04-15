"""Integration-style tests across scheduler output and RAG modules."""

from ai_explainer import explain_schedule
from knowledge_base import SemanticRetriever
from pawpal_system import Pet, PetOwner, Scheduler, Task


class _FakeClient:
    def generate_content(self, _prompt: str):
        class _Response:
            text = "Integrated explanation"

        return _Response()


def _simple_embedder(text: str):
    lowered = text.lower()
    return [
        float(len(lowered)),
        float(lowered.count("walk") + lowered.count("exercise")),
        float(lowered.count("feed") + lowered.count("meal")),
        float(lowered.count("med") + lowered.count("medicine")),
    ]


def test_scheduler_plan_feeds_rag_pipeline() -> None:
    scheduler = Scheduler()
    scheduler.set_pet(Pet("Mochi", "dog"))
    scheduler.set_owner(PetOwner("Jordan", availability=(480, 1320)))

    assert scheduler.add_task(Task("Morning walk", "walk", 30, "high", time_window=(480, 700)))
    assert scheduler.add_task(Task("Breakfast", "feed", 15, "medium", time_window=(540, 720)))

    plan = scheduler.generate_plan()
    assert len(plan) >= 2

    retriever = SemanticRetriever(similarity_threshold=0.0, embedding_backend=_simple_embedder)
    retrieved = retriever.retrieve_for_plan(plan, pet=scheduler.pet)

    explanation = explain_schedule(
        plan_items=plan,
        retrieved_facts=retrieved,
        pet=scheduler.pet,
        owner=scheduler.owner,
        client=_FakeClient(),
    )

    assert explanation == "Integrated explanation"
    assert "Morning walk" in retrieved
