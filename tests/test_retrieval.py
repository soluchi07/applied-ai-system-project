"""Tests for knowledge retrieval behavior."""

from knowledge_base import PET_CARE_FACTS, SemanticRetriever
from pawpal_system import Pet, PlanItem, Task


def _simple_embedder(text: str):
    lowered = text.lower()
    return [
        float(len(lowered)),
        float(lowered.count("walk") + lowered.count("exercise")),
        float(lowered.count("feed") + lowered.count("meal")),
        float(lowered.count("med") + lowered.count("medicine")),
        float(lowered.count("groom") + lowered.count("brush")),
    ]


def test_retrieve_top_k_ranked_results() -> None:
    retriever = SemanticRetriever(
        facts=PET_CARE_FACTS,
        top_k=3,
        similarity_threshold=0.0,
        embedding_backend=_simple_embedder,
    )

    results = retriever.retrieve("morning walk exercise routine for dog", species="dog")

    assert len(results) == 3
    assert results[0].score >= results[1].score >= results[2].score


def test_retrieve_returns_empty_when_threshold_too_high() -> None:
    retriever = SemanticRetriever(
        facts=PET_CARE_FACTS,
        top_k=3,
        similarity_threshold=1.01,
        embedding_backend=_simple_embedder,
    )

    results = retriever.retrieve("random unrelated phrase", species="dog")

    assert results == []


def test_retrieve_for_plan_maps_each_task() -> None:
    retriever = SemanticRetriever(
        facts=PET_CARE_FACTS,
        top_k=2,
        similarity_threshold=0.0,
        embedding_backend=_simple_embedder,
    )

    walk_task = Task("Morning walk", "walk", 30, "high")
    feed_task = Task("Breakfast", "feed", 15, "medium")
    plan_items = [
        PlanItem(task=walk_task, scheduled_time=540, duration_minutes=30, reason="test"),
        PlanItem(task=feed_task, scheduled_time=600, duration_minutes=15, reason="test"),
    ]

    results = retriever.retrieve_for_plan(plan_items, pet=Pet("Mochi", "dog"))

    assert "Morning walk" in results
    assert "Breakfast" in results
    assert len(results["Morning walk"]) <= 2
    assert len(results["Breakfast"]) <= 2
