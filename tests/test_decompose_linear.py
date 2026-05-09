"""Tests LinearDecomposer."""

from __future__ import annotations

import pytest

from recherche_mcp.decompose import LinearDecomposer
from recherche_mcp.models import Domain, Question, Strategy


@pytest.mark.integ
def test_linear_produces_default_5_subq(question_clinique):
    plan = LinearDecomposer().decompose(question_clinique)
    assert len(plan.sub_questions) == 5
    assert plan.strategy == Strategy.LINEAR
    assert all(0.0 <= s.confidence <= 1.0 for s in plan.sub_questions)
    assert plan.edges == []  # Linear = pas de graphe


@pytest.mark.unit
@pytest.mark.parametrize("bad", [3, 8, 0, -1])
def test_linear_rejects_out_of_range(bad):
    with pytest.raises(ValueError, match="n_subq must be in"):
        LinearDecomposer(n_subq=bad)


@pytest.mark.integ
def test_linear_with_n_4_to_7(question_clinique):
    for n in [4, 5, 6, 7]:
        plan = LinearDecomposer(n_subq=n).decompose(question_clinique)
        assert len(plan.sub_questions) == n


@pytest.mark.integ
def test_linear_dispatch_covers_all_subq(question_clinique):
    plan = LinearDecomposer().decompose(question_clinique)
    sq_ids = {s.id for s in plan.sub_questions}
    dispatch_ids = {d.sub_question_id for d in plan.dispatch}
    assert sq_ids == dispatch_ids


@pytest.mark.integ
def test_linear_quality_has_all_6_criteria(question_clinique):
    plan = LinearDecomposer().decompose(question_clinique)
    q = plan.quality
    assert all(
        0.0 <= getattr(q, k) <= 1.0
        for k in (
            "couverture",
            "orthogonalite",
            "autonomie",
            "clarte",
            "balance",
            "tracabilite",
        )
    )
