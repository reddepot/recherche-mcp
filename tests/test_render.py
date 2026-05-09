"""Tests templating Jinja2."""

from __future__ import annotations

import pytest

from recherche_mcp.decompose import LinearDecomposer
from recherche_mcp.models import Domain, Question
from recherche_mcp.prompts.render import render_subprompts


@pytest.mark.integ
def test_render_produces_one_prompt_per_subq(question_clinique):
    plan = LinearDecomposer().decompose(question_clinique)
    out = render_subprompts(plan)
    assert len(out) == len(plan.sub_questions)
    for r in out:
        assert "sub_question_id" in r
        assert "prompt" in r
        assert len(r["prompt"]) > 100


@pytest.mark.integ
def test_render_clinique_template_includes_keywords(question_clinique):
    plan = LinearDecomposer().decompose(question_clinique)
    out = render_subprompts(plan)
    # Au moins un prompt doit inclure des éléments clinique-spécifiques
    full = " ".join(r["prompt"] for r in out)
    assert "médecin du travail" in full or "HAS" in full
    assert "INRS" in full or "CSP" in full


@pytest.mark.integ
def test_render_fallback_to_mixte_for_unknown_domain():
    """Si domain_hint est mixte, doit utiliser domain_mixte.j2."""
    q = Question(text="x" * 50, domain=Domain.MIXTE)
    plan = LinearDecomposer().decompose(q)
    out = render_subprompts(plan)
    assert all("Expert généraliste" in r["prompt"] for r in out)
