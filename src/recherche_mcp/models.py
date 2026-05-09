"""Pydantic schemas — source de vérité des structures de données."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


class Domain(StrEnum):
    """Domaines de questions reconnus par le pipeline de décomposition."""

    CLINIQUE = "clinique"
    JURIDIQUE_FR = "juridique_fr"
    TECHNIQUE = "technique"
    MULTILINGUE = "multilingue"
    MIXTE = "mixte"


class Strategy(StrEnum):
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
    domain: Domain = Domain.MIXTE  # contexte de pondération de overall

    @property
    def overall(self) -> float:
        """Score global pondéré par domaine.

        Les poids des 6 critères sont chargés depuis `quality_weights.yaml`
        et reflètent les priorités métier par domaine (cf ADR-0002).
        """
        from .quality import get_weights_for_domain  # lazy import (évite circular)
        weights = get_weights_for_domain(self.domain)
        criteria = ("couverture", "orthogonalite", "autonomie", "clarte", "balance", "tracabilite")
        return sum(weights[k] * getattr(self, k) for k in criteria)


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
    def _dispatch_covers_subq(
        cls, v: list[DispatchEntry], info: ValidationInfo
    ) -> list[DispatchEntry]:
        """Dispatch couvre exactement les sub_questions, sans doublons."""
        sq_ids = {s.id for s in info.data.get("sub_questions", [])}
        d_ids = [d.sub_question_id for d in v]
        # Anti-doublons : un sub_question_id ne doit apparaître qu'une fois
        if len(d_ids) != len(set(d_ids)):
            raise ValueError(
                "dispatch contient des sub_question_id dupliqués"
            )
        if sq_ids != set(d_ids):
            raise ValueError(
                "dispatch doit couvrir exactement les sub_questions"
            )
        return v

    @model_validator(mode="after")
    def _edges_reference_existing_subqs(self) -> "ResearchPlan":
        """Intégrité référentielle : tous les edges pointent vers des
        sub_questions existantes. Empêche les graphes rompus en silence.
        """
        sq_ids = {s.id for s in self.sub_questions}
        for edge in self.edges:
            if edge.source_id not in sq_ids:
                raise ValueError(
                    f"edge.source_id={edge.source_id} absent de sub_questions"
                )
            if edge.target_id not in sq_ids:
                raise ValueError(
                    f"edge.target_id={edge.target_id} absent de sub_questions"
                )
        return self
