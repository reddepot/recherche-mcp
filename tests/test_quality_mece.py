"""Tests qualité MECE — orthogonalité, couverture, balance."""

from __future__ import annotations

import pytest

from recherche_mcp.decompose import LinearDecomposer, GraphDecomposer
from recherche_mcp.models import Domain, Question


PHASE_A_ORTHO_BASELINE = 0.05
"""Phase A heuristique pure : seuil bas car sans LLM, la diversité textuelle
est limitée à la formulation par axe + extraction de sujet court.
Phase B LLM-driven cible 0.4+ (cosine max ≤ 0.6)."""


@pytest.mark.integ
def test_mece_orthogonality_baseline_linear(cases_fixture):
    """Phase A baseline : orthogonalité > 0.05 (heuristique sans LLM).

    Phase B cible : ≥ 0.4 avec LLM-driven decomposition.
    """
    failed = []
    for case in cases_fixture:
        q = Question(text=case["question"], domain=Domain(case["domain"]))
        plan = LinearDecomposer().decompose(q)
        if plan.quality.orthogonalite < PHASE_A_ORTHO_BASELINE:
            failed.append((case["name"], plan.quality.orthogonalite))
    assert not failed, (
        f"Cas avec orthogonalité < {PHASE_A_ORTHO_BASELINE} (baseline Phase A) : "
        f"{failed}"
    )


@pytest.mark.integ
def test_mece_orthogonality_baseline_graph(cases_fixture):
    """Phase A baseline graphe : orthogonalité > 0.05."""
    failed = []
    for case in cases_fixture:
        q = Question(text=case["question"], domain=Domain(case["domain"]))
        plan = GraphDecomposer().decompose(q)
        if plan.quality.orthogonalite < PHASE_A_ORTHO_BASELINE:
            failed.append((case["name"], plan.quality.orthogonalite))
    assert not failed, (
        f"Graph cas avec orthogonalité < {PHASE_A_ORTHO_BASELINE} (baseline Phase A) : "
        f"{failed}"
    )


@pytest.mark.integ
def test_quality_overall_in_range(cases_fixture):
    """Tous scores overall doivent être dans [0, 1]."""
    for case in cases_fixture:
        q = Question(text=case["question"], domain=Domain(case["domain"]))
        plan = LinearDecomposer().decompose(q)
        assert 0.0 <= plan.quality.overall <= 1.0


@pytest.mark.integ
def test_traceability_higher_for_graph(question_clinique):
    """Graph doit avoir une traçabilité ≥ Linear (présence d'edges)."""
    lin = LinearDecomposer().decompose(question_clinique)
    grf = GraphDecomposer().decompose(question_clinique)
    assert grf.quality.tracabilite >= lin.quality.tracabilite
