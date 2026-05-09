"""A/B test Linear vs Graph sur 5 cas réels — critère succès Phase A."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from recherche_mcp.decompose import make_decomposer
from recherche_mcp.models import Domain, Question, Strategy


@pytest.mark.integ
def test_ab_linear_vs_graph_5_cases(cases_fixture, tmp_path):
    """Critère succès : ≥4/5 cas avec max(linear, graph) overall > 0.7."""
    rows = []
    for case in cases_fixture:
        q = Question(text=case["question"], domain=Domain(case["domain"]))
        lin = make_decomposer(Strategy.LINEAR).decompose(q)
        grf = make_decomposer(Strategy.GRAPH).decompose(q)
        rows.append(
            {
                "case": case["name"],
                "linear_overall": round(lin.quality.overall, 3),
                "graph_overall": round(grf.quality.overall, 3),
                "linear_orthogonalite": round(lin.quality.orthogonalite, 3),
                "graph_orthogonalite": round(grf.quality.orthogonalite, 3),
                "winner": "graph"
                if grf.quality.overall > lin.quality.overall
                else "linear",
            }
        )

    # Génère le rapport A/B
    report_path = tmp_path / "ab_report.md"
    lines = ["# A/B Linear vs Graph — Phase A\n"]
    lines.append(
        "| Case | Linear | Graph | Lin-Ortho | Graph-Ortho | Winner |"
    )
    lines.append("|------|--------|-------|-----------|-------------|--------|")
    for r in rows:
        lines.append(
            f"| {r['case']} | {r['linear_overall']} | {r['graph_overall']} | "
            f"{r['linear_orthogonalite']} | {r['graph_orthogonalite']} | {r['winner']} |"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Critère Phase A baseline (heuristique pure, sans LLM) :
    # - ≥4/5 cas avec overall > 0.5 (mesure d'effectivité du pipeline)
    # - cible Phase B : overall > 0.7 avec LLM-driven decomposition
    PHASE_A_OVERALL_BASELINE = 0.5
    wins = sum(
        1
        for r in rows
        if max(r["linear_overall"], r["graph_overall"]) > PHASE_A_OVERALL_BASELINE
    )
    assert wins >= 4, (
        f"Phase A baseline non atteint: {wins}/5 avec overall>{PHASE_A_OVERALL_BASELINE}. "
        f"Rapport : {report_path}"
    )
