"""Pydantic schemas — source de vérité des structures de données."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Domain(str, Enum):
    CLINIQUE = "clinique"
    JURIDIQUE_FR = "juridique_fr"
    TECHNIQUE = "technique"
    MULTILINGUE = "multilingue"
    MIXTE = "mixte"


class Strategy(str, Enum):
    LINEAR = "linear"
    GRAPH = "graph"


def _now() -> datetime:
    """UTC-aware now (datetime.utcnow() is deprecated in 3.13)."""
    return datetime.now(UTC)


class Question(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str = Field(min_length=10, max_length=4000)
    domain: Domain | None = None
    created_at: datetime = Field(default_factory=_now)


class SubQuestion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    parent_id: UUID
    text: str
    rationale: str
    domain_hint: Domain
    confidence: float = Field(ge=0.0, le=1.0)


class GraphEdge(BaseModel):
    source_id: UUID
    target_id: UUID
    relation: Literal["depends_on", "informs", "constrains"]


class ModelCandidate(BaseModel):
    name: str
    rationale: str
    invocation: Literal["auto", "manual"]
    priority: int = Field(ge=1, le=3)


class DispatchEntry(BaseModel):
    sub_question_id: UUID
    candidates: list[ModelCandidate] = Field(min_length=1, max_length=3)


class QualityScores(BaseModel):
    couverture: float = Field(ge=0.0, le=1.0)
    orthogonalite: float = Field(ge=0.0, le=1.0)
    autonomie: float = Field(ge=0.0, le=1.0)
    clarte: float = Field(ge=0.0, le=1.0)
    balance: float = Field(ge=0.0, le=1.0)
    tracabilite: float = Field(ge=0.0, le=1.0)

    @property
    def overall(self) -> float:
        """Phase A: moyenne simple.

        DSPY_GATE: pondération = trigger DSPy Phase B
        (cf decompose.py header).
        """
        v = self.model_dump()
        return sum(v.values()) / len(v)


class ResearchPlan(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    question: Question
    strategy: Strategy
    sub_questions: list[SubQuestion] = Field(min_length=4, max_length=7)
    edges: list[GraphEdge] = Field(default_factory=list)
    dispatch: list[DispatchEntry]
    quality: QualityScores
    created_at: datetime = Field(default_factory=_now)

    @field_validator("dispatch")
    @classmethod
    def _dispatch_covers_subq(cls, v, info):
        sq_ids = {s.id for s in info.data.get("sub_questions", [])}
        d_ids = {d.sub_question_id for d in v}
        if sq_ids != d_ids:
            raise ValueError("dispatch doit couvrir exactement les sub_questions")
        return v
