"""Tests Pydantic schemas — base de la pyramide."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from recherche_mcp.models import (
    DispatchEntry,
    Domain,
    GraphEdge,
    ModelCandidate,
    Question,
    QualityScores,
    ResearchPlan,
    Strategy,
    SubQuestion,
)


@pytest.mark.unit
def test_question_minimum_length():
    with pytest.raises(ValidationError):
        Question(text="court")  # 5 chars < min_length=10


@pytest.mark.unit
def test_question_with_domain():
    q = Question(text="x" * 50, domain=Domain.CLINIQUE)
    assert q.domain == Domain.CLINIQUE
    assert q.id is not None


@pytest.mark.unit
def test_subquestion_confidence_range():
    parent = uuid4()
    with pytest.raises(ValidationError):
        SubQuestion(
            parent_id=parent,
            text="x",
            rationale="y",
            domain_hint=Domain.MIXTE,
            confidence=1.5,
        )


@pytest.mark.unit
def test_modelcandidate_priority_range():
    with pytest.raises(ValidationError):
        ModelCandidate(name="x", rationale="y", invocation="auto", priority=4)


@pytest.mark.unit
def test_quality_scores_overall_average():
    s = QualityScores(
        couverture=0.5,
        orthogonalite=0.5,
        autonomie=0.5,
        clarte=0.5,
        balance=0.5,
        tracabilite=0.5,
    )
    assert abs(s.overall - 0.5) < 1e-9


@pytest.mark.unit
def test_research_plan_dispatch_must_cover_subq():
    q = Question(text="x" * 50)
    sq_a = SubQuestion(
        parent_id=q.id,
        text="[def] ...",
        rationale="rationale long enough to pass",
        domain_hint=Domain.MIXTE,
        confidence=0.7,
    )
    sq_b = SubQuestion(
        parent_id=q.id,
        text="[etat] ...",
        rationale="rationale long enough to pass",
        domain_hint=Domain.MIXTE,
        confidence=0.7,
    )
    sq_c = SubQuestion(
        parent_id=q.id,
        text="[cadre] ...",
        rationale="rationale long enough to pass",
        domain_hint=Domain.MIXTE,
        confidence=0.7,
    )
    sq_d = SubQuestion(
        parent_id=q.id,
        text="[op] ...",
        rationale="rationale long enough to pass",
        domain_hint=Domain.MIXTE,
        confidence=0.7,
    )

    cand = ModelCandidate(
        name="x", rationale="y", invocation="auto", priority=1
    )
    quality = QualityScores(
        couverture=0.7,
        orthogonalite=0.7,
        autonomie=0.7,
        clarte=0.7,
        balance=0.7,
        tracabilite=0.7,
    )

    # Dispatch couvre exactement les sous-Q : OK
    plan = ResearchPlan(
        question=q,
        strategy=Strategy.LINEAR,
        sub_questions=[sq_a, sq_b, sq_c, sq_d],
        dispatch=[
            DispatchEntry(sub_question_id=sq_a.id, candidates=[cand]),
            DispatchEntry(sub_question_id=sq_b.id, candidates=[cand]),
            DispatchEntry(sub_question_id=sq_c.id, candidates=[cand]),
            DispatchEntry(sub_question_id=sq_d.id, candidates=[cand]),
        ],
        quality=quality,
    )
    assert plan.id is not None

    # Dispatch incomplet : ValidationError
    with pytest.raises(ValidationError):
        ResearchPlan(
            question=q,
            strategy=Strategy.LINEAR,
            sub_questions=[sq_a, sq_b, sq_c, sq_d],
            dispatch=[
                DispatchEntry(sub_question_id=sq_a.id, candidates=[cand]),
            ],
            quality=quality,
        )


@pytest.mark.unit
def test_research_plan_min_4_subq():
    q = Question(text="x" * 50)
    quality = QualityScores(
        couverture=0.7,
        orthogonalite=0.7,
        autonomie=0.7,
        clarte=0.7,
        balance=0.7,
        tracabilite=0.7,
    )
    with pytest.raises(ValidationError):
        ResearchPlan(
            question=q,
            strategy=Strategy.LINEAR,
            sub_questions=[],  # 0 < 4
            dispatch=[],
            quality=quality,
        )
