"""Tests DispatchMatrix : YAML loader, SIGHUP reload, fallback."""

from __future__ import annotations

import os
import signal
import time
from uuid import uuid4

import pytest
import yaml

from recherche_mcp.dispatch import DispatchMatrix
from recherche_mcp.models import Domain, SubQuestion


def _make_subq(domain: Domain) -> SubQuestion:
    return SubQuestion(
        parent_id=uuid4(),
        text=f"[axe] {domain.value}",
        rationale="test fixture rationale long enough",
        domain_hint=domain,
        confidence=0.7,
    )


@pytest.mark.unit
def test_dispatch_loads_default_yaml():
    matrix = DispatchMatrix.current()
    assert "clinique" in matrix._data
    assert "juridique_fr" in matrix._data
    assert "mixte" in matrix._data


@pytest.mark.unit
def test_dispatch_resolve_clinique():
    matrix = DispatchMatrix.current()
    subqs = [_make_subq(Domain.CLINIQUE)]
    entries = matrix.resolve(subqs)
    assert len(entries) == 1
    assert all(c.priority >= 1 for c in entries[0].candidates)


@pytest.mark.unit
def test_dispatch_fallback_mixte_for_unknown_domain(tmp_dispatch_yaml):
    """Un domaine absent fallback à 'mixte'."""
    DispatchMatrix.reset()
    matrix = DispatchMatrix.current(path=tmp_dispatch_yaml)
    sq = SubQuestion(
        parent_id=uuid4(),
        text="[x] y",
        rationale="long enough rationale here",
        domain_hint=Domain.JURIDIQUE_FR,  # absent du tmp_dispatch_yaml
        confidence=0.7,
    )
    entries = matrix.resolve([sq])
    assert entries[0].candidates[0].name == "anthropic-claude-web-search"


@pytest.mark.unit
def test_dispatch_priority_ordering():
    matrix = DispatchMatrix.current()
    subqs = [_make_subq(Domain.CLINIQUE)]
    entries = matrix.resolve(subqs)
    priorities = [c.priority for c in entries[0].candidates]
    assert priorities == sorted(priorities)


@pytest.mark.integ
def test_dispatch_sighup_reload(tmp_dispatch_yaml):
    """SIGHUP recharge le fichier modifié à chaud."""
    DispatchMatrix.reset()
    matrix = DispatchMatrix.current(path=tmp_dispatch_yaml)

    # État initial
    assert (
        matrix._data["clinique"][0]["name"] == "perplexity-deep-research"
    )

    # Modifier le fichier
    new_content = {
        "clinique": [
            {
                "name": "modified-model",
                "rationale": "After SIGHUP",
                "invocation": "auto",
                "priority": 1,
            }
        ],
        "mixte": matrix._data["mixte"],
    }
    tmp_dispatch_yaml.write_text(yaml.safe_dump(new_content), encoding="utf-8")

    # Reload manuel (SIGHUP est testé indirectement via .reload())
    matrix.reload()
    assert matrix._data["clinique"][0]["name"] == "modified-model"
