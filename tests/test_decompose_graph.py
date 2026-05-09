"""Tests GraphDecomposer — DAG, edges, structure."""

from __future__ import annotations

import pytest

from recherche_mcp.decompose import GraphDecomposer
from recherche_mcp.models import Domain, Question, Strategy


@pytest.mark.integ
def test_graph_produces_default_5_subq(question_clinique):
    plan = GraphDecomposer().decompose(question_clinique)
    assert len(plan.sub_questions) == 5
    assert plan.strategy == Strategy.GRAPH


@pytest.mark.integ
def test_graph_has_root_and_synthesis(question_clinique):
    plan = GraphDecomposer().decompose(question_clinique)
    texts = [s.text for s in plan.sub_questions]
    assert any("[définition]" in t for t in texts)
    assert any("[synthèse]" in t for t in texts)


@pytest.mark.integ
def test_graph_edges_form_dag(question_clinique):
    """Vérifie que les edges forment un DAG (pas de cycle)."""
    plan = GraphDecomposer().decompose(question_clinique)
    assert len(plan.edges) > 0

    # Construction du graphe
    adj: dict = {}
    for e in plan.edges:
        adj.setdefault(e.source_id, []).append(e.target_id)

    # DFS détection cycle
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {s.id: WHITE for s in plan.sub_questions}

    def dfs(node):
        color[node] = GRAY
        for nbr in adj.get(node, []):
            if color.get(nbr) == GRAY:
                raise AssertionError(f"Cycle détecté: {node} -> {nbr}")
            if color.get(nbr) == WHITE:
                dfs(nbr)
        color[node] = BLACK

    for n in list(color.keys()):
        if color[n] == WHITE:
            dfs(n)


@pytest.mark.integ
def test_graph_branches_link_root_to_synthesis(question_clinique):
    plan = GraphDecomposer(n_subq=5).decompose(question_clinique)
    # 1 root + 3 branches + 1 synth = 5
    # edges : 3 root->branch (informs) + 3 branch->synth (depends_on) = 6
    assert len(plan.edges) == 6
    informs = [e for e in plan.edges if e.relation == "informs"]
    depends = [e for e in plan.edges if e.relation == "depends_on"]
    assert len(informs) == 3
    assert len(depends) == 3


@pytest.mark.unit
@pytest.mark.parametrize("bad", [3, 8, 0])
def test_graph_rejects_out_of_range(bad):
    with pytest.raises(ValueError, match="n_subq must be in"):
        GraphDecomposer(n_subq=bad)


@pytest.mark.integ
def test_graph_edges_reference_existing_subqs(question_clinique):
    """POLYLENS Gemini P0 : edges doivent référencer des sub_questions existantes."""
    plan = GraphDecomposer().decompose(question_clinique)
    sq_ids = {s.id for s in plan.sub_questions}
    for edge in plan.edges:
        assert edge.source_id in sq_ids, f"source_id orphelin: {edge.source_id}"
        assert edge.target_id in sq_ids, f"target_id orphelin: {edge.target_id}"
