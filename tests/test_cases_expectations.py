"""Tests paramétriques sur cases.yaml — vérifier que `expected_subq` matchent (Kimi P2)."""

from __future__ import annotations

import pytest

from recherche_mcp.decompose import LinearDecomposer
from recherche_mcp.models import Domain, Question


def _extract_axis_label(text: str) -> str:
    """Extrait l'axe entre crochets en début de sous-Q."""
    if text.startswith("[") and "]" in text:
        return text.split("]", 1)[0].lstrip("[").strip()
    return ""


@pytest.mark.integ
@pytest.mark.parametrize("case_idx", range(5))
def test_case_expected_axes_present(cases_fixture, case_idx):
    """Audit Kimi P2 : `expected_subq` documenté doit matcher les axes produits.

    Vérifie que les labels d'axes attendus dans cases.yaml sont effectivement
    présents dans la décomposition. Faux positif acceptable (axe en plus OK),
    faux négatif rejeté (axe manquant = échec).
    """
    case = cases_fixture[case_idx]
    q = Question(text=case["question"], domain=Domain(case["domain"]))
    plan = LinearDecomposer().decompose(q)

    produced_labels = {
        _extract_axis_label(s.text) for s in plan.sub_questions
    }
    expected_labels = {
        _extract_axis_label(s) for s in case.get("expected_subq", [])
    }
    expected_labels.discard("")  # filtre vides

    # Au moins 1 axe attendu doit être présent (Phase A baseline).
    # Phase B avec LLM-driven : viser couverture ≥ 80%.
    if expected_labels:
        intersection = produced_labels & expected_labels
        assert intersection, (
            f"Cas '{case['name']}' : ZÉRO axe attendu présent. "
            f"Attendus={expected_labels}, produits={produced_labels}. "
            f"Soit ajuster cases.yaml.expected_subq pour utiliser les "
            f"labels canoniques de axes_by_domain.yaml, soit améliorer la "
            f"décomposition Phase B (LLM-driven)."
        )


@pytest.mark.integ
@pytest.mark.parametrize("case_idx", range(5))
def test_case_expected_dispatch_present(cases_fixture, case_idx):
    """Au moins 1 modèle de `expected_dispatch` doit apparaître dans dispatch produit."""
    case = cases_fixture[case_idx]
    q = Question(text=case["question"], domain=Domain(case["domain"]))
    plan = LinearDecomposer().decompose(q)

    produced_models = {
        c.name for entry in plan.dispatch for c in entry.candidates
    }
    expected_models = set(case.get("expected_dispatch", []))

    if expected_models:
        intersection = produced_models & expected_models
        assert intersection, (
            f"Cas '{case['name']}' : aucun modèle attendu présent. "
            f"Attendus={expected_models}, produits={produced_models}"
        )


@pytest.mark.integ
@pytest.mark.parametrize("case_idx", range(5))
def test_case_confidence_minimum(cases_fixture, case_idx):
    """confidence des sous-Q produites ≥ 0.7 (baseline Phase A heuristique)."""
    case = cases_fixture[case_idx]
    q = Question(text=case["question"], domain=Domain(case["domain"]))
    plan = LinearDecomposer().decompose(q)

    confidences = [s.confidence for s in plan.sub_questions]
    avg_confidence = sum(confidences) / len(confidences)
    assert avg_confidence >= 0.7, (
        f"Cas '{case['name']}' : confidence moyenne {avg_confidence:.2f} < 0.7"
    )
