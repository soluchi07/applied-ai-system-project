"""Knowledge base and semantic retrieval for PawPal+ RAG explanations."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import math
import re
from typing import Callable, Dict, Iterable, List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from pawpal_system import Pet, PlanItem, Task


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CareFact:
    """A normalized pet-care fact used for retrieval."""

    text: str
    species: str
    tags: Sequence[str]
    topic: str


@dataclass(frozen=True)
class RetrievedFact:
    """A retrieval result with similarity score."""

    text: str
    score: float
    topic: str


PET_CARE_FACTS: List[CareFact] = [
    CareFact("Dogs usually need 30 to 60 minutes of exercise each day split across one to three sessions.", "dog", ["walk", "exercise", "energy"], "exercise"),
    CareFact("Most adult cats benefit from at least 15 minutes of interactive play daily to reduce stress and boredom.", "cat", ["play", "exercise", "enrichment"], "exercise"),
    CareFact("High-energy dog breeds often need a longer morning activity block to reduce disruptive behavior later in the day.", "dog", ["walk", "morning", "behavior"], "exercise"),
    CareFact("Puppies should have shorter, more frequent activity sessions and regular rest breaks.", "dog", ["puppy", "rest", "exercise"], "exercise"),
    CareFact("Adult dogs are typically fed once or twice daily at consistent times to support digestion and routine.", "dog", ["feed", "meal", "routine"], "nutrition"),
    CareFact("Many cats do best with two or three smaller meals spread through the day rather than a single large meal.", "cat", ["feed", "meal", "routine"], "nutrition"),
    CareFact("Fresh water should be available throughout the day, and bowls should be cleaned regularly.", "all", ["water", "hydration", "daily"], "nutrition"),
    CareFact("After vigorous activity, allow a cool-down period before feeding to reduce stomach upset risk in dogs.", "dog", ["feed", "walk", "timing"], "nutrition"),
    CareFact("Administer medications at the same time each day when possible to improve adherence.", "all", ["medication", "timing", "routine"], "medical"),
    CareFact("Some medications are best given with food; scheduling meds after meals can reduce GI side effects.", "all", ["medication", "feed", "timing"], "medical"),
    CareFact("Observation checks after medication can help catch side effects early.", "all", ["medication", "monitor", "safety"], "medical"),
    CareFact("Post-procedure pets often need reduced activity and extra rest windows for recovery.", "all", ["rest", "recovery", "medical"], "medical"),
    CareFact("Regular grooming helps detect skin issues earlier and lowers matting risk.", "all", ["groom", "health", "coat"], "grooming"),
    CareFact("Long-haired cats often need brushing multiple times per week to prevent painful mats.", "cat", ["groom", "brush", "coat"], "grooming"),
    CareFact("Bathing frequency for most dogs is often monthly or as advised by a vet, not daily.", "dog", ["groom", "bath", "skin"], "grooming"),
    CareFact("Short training sessions with positive reinforcement improve consistency better than infrequent long sessions.", "all", ["training", "behavior", "routine"], "behavior"),
    CareFact("Mentally enriching activities can reduce destructive behavior in both cats and dogs.", "all", ["enrichment", "play", "behavior"], "behavior"),
    CareFact("Scheduling demanding tasks earlier in available owner windows can reduce skipped tasks later in the day.", "all", ["priority", "schedule", "consistency"], "planning"),
    CareFact("Buffer time between tasks helps avoid cascading delays when one task runs long.", "all", ["buffer", "schedule", "planning"], "planning"),
    CareFact("When no clear guideline applies, it is safer to acknowledge uncertainty and follow vet-specific instructions.", "all", ["safety", "guardrail", "vet"], "safety"),
]


class SemanticRetriever:
    """Embedding-first retriever with deterministic fallback embeddings."""

    def __init__(
        self,
        facts: Optional[Sequence[CareFact]] = None,
        top_k: int = 3,
        similarity_threshold: float = 0.2,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_backend: Optional[Callable[[str], Sequence[float]]] = None,
    ) -> None:
        self.facts: List[CareFact] = list(facts or PET_CARE_FACTS)
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.model_name = model_name
        self.embedding_backend = embedding_backend
        self._cache: Dict[str, List[float]] = {}
        self._sentence_model = None
        self._model_load_attempted = False

    def retrieve_for_task(self, task: "Task", pet: Optional["Pet"] = None, top_k: Optional[int] = None) -> List[RetrievedFact]:
        """Retrieve top facts for a single task."""
        query = self._build_task_query(task, pet=pet)
        return self.retrieve(query=query, species=(pet.species if pet else None), top_k=top_k)

    def retrieve_for_plan(self, plan_items: Sequence["PlanItem"], pet: Optional["Pet"] = None, top_k: Optional[int] = None) -> Dict[str, List[RetrievedFact]]:
        """Retrieve top facts for each plan item keyed by task title."""
        results: Dict[str, List[RetrievedFact]] = {}
        for item in plan_items:
            results[item.task.title] = self.retrieve_for_task(item.task, pet=pet, top_k=top_k)
        return results

    def retrieve(self, query: str, species: Optional[str] = None, top_k: Optional[int] = None) -> List[RetrievedFact]:
        """Retrieve top-k facts by cosine similarity and threshold."""
        cleaned_query = self._normalize_text(query)
        query_vector = self._embed(cleaned_query)
        filtered_facts = self._filter_facts_by_species(species)

        scored: List[RetrievedFact] = []
        for fact in filtered_facts:
            similarity = self._cosine_similarity(query_vector, self._embed(fact.text))
            if similarity >= self.similarity_threshold:
                scored.append(
                    RetrievedFact(
                        text=fact.text,
                        score=similarity,
                        topic=fact.topic,
                    )
                )

        scored.sort(key=lambda item: (-item.score, item.topic, item.text))
        k = top_k if top_k is not None else self.top_k
        top_results = scored[:k]

        logger.info(
            "Retrieval query='%s' species='%s' matched=%d returned=%d",
            query,
            species,
            len(scored),
            len(top_results),
        )
        return top_results

    def _filter_facts_by_species(self, species: Optional[str]) -> Iterable[CareFact]:
        if not species:
            return self.facts
        normalized_species = species.strip().lower()
        return [fact for fact in self.facts if fact.species in ("all", normalized_species)]

    def _build_task_query(self, task: "Task", pet: Optional["Pet"] = None) -> str:
        pet_species = pet.species if pet else ""
        return " ".join(
            part
            for part in [
                task.title,
                task.task_type,
                task.notes,
                task.priority,
                pet_species,
            ]
            if part
        )

    def _embed(self, text: str) -> List[float]:
        if text in self._cache:
            return self._cache[text]

        if self.embedding_backend is not None:
            vector = self._to_float_list(self.embedding_backend(text))
        else:
            model = self._load_sentence_transformer()
            if model is not None:
                vector = self._to_float_list(model.encode(text))
            else:
                vector = self._fallback_embed(text)

        self._cache[text] = vector
        return vector

    def _load_sentence_transformer(self):
        if self._model_load_attempted:
            return self._sentence_model

        self._model_load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._sentence_model = SentenceTransformer(self.model_name)
            logger.info("Loaded sentence-transformer model: %s", self.model_name)
        except Exception as exc:  # pragma: no cover - environment-dependent path
            logger.warning(
                "Falling back to deterministic embeddings because sentence-transformers was unavailable: %s",
                exc,
            )
            self._sentence_model = None

        return self._sentence_model

    def _fallback_embed(self, text: str, dimensions: int = 96) -> List[float]:
        """Generate deterministic token-hash embeddings when model loading fails."""
        tokens = self._normalize_text(text).split()
        if not tokens:
            return [0.0] * dimensions

        vector = [0.0] * dimensions
        for token in tokens:
            bucket = hash(token) % dimensions
            sign = 1.0 if (hash(token + "_sign") % 2 == 0) else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return [0.0] * dimensions
        return [value / norm for value in vector]

    def _cosine_similarity(self, left: Sequence[float], right: Sequence[float]) -> float:
        if not left or not right:
            return 0.0

        dimensions = min(len(left), len(right))
        if dimensions == 0:
            return 0.0

        dot_product = sum(left[i] * right[i] for i in range(dimensions))
        left_norm = math.sqrt(sum(left[i] * left[i] for i in range(dimensions)))
        right_norm = math.sqrt(sum(right[i] * right[i] for i in range(dimensions)))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.strip().lower())

    def _to_float_list(self, vector: Sequence[float]) -> List[float]:
        return [float(value) for value in vector]
