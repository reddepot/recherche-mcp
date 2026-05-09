"""Tests DispatchMatrix : YAML loader, SIGHUP reload, fallback."""

from __future__ import annotations

import os
import signal
import threading
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
def test_dispatch_reload_after_yaml_modification(tmp_dispatch_yaml):
    """reload() recharge le fichier modifié à chaud (test découplé du SIGHUP)."""
    DispatchMatrix.reset()
    matrix = DispatchMatrix.current(path=tmp_dispatch_yaml)

    assert matrix._data["clinique"][0]["name"] == "perplexity-deep-research"

    new_content = {
        "clinique": [
            {
                "name": "modified-model",
                "rationale": "After reload",
                "invocation": "auto",
                "priority": 1,
            }
        ],
        "mixte": matrix._data["mixte"],
    }
    tmp_dispatch_yaml.write_text(yaml.safe_dump(new_content), encoding="utf-8")

    matrix.reload()
    assert matrix._data["clinique"][0]["name"] == "modified-model"


@pytest.mark.integ
def test_dispatch_real_sighup_triggers_reload(tmp_dispatch_yaml):
    """SIGHUP réel déclenche le reload (POLYLENS CONV-3 fix).

    Skip sur Windows (pas de SIGHUP) et thread non-main (signal handlers
    ne fonctionnent que sur le thread principal).
    """
    if not hasattr(signal, "SIGHUP"):
        pytest.skip("SIGHUP non disponible (Windows ?)")
    if threading.current_thread() is not threading.main_thread():
        pytest.skip("SIGHUP handlers uniquement sur thread principal")

    DispatchMatrix.reset()
    matrix = DispatchMatrix.current(path=tmp_dispatch_yaml)
    assert matrix._data["clinique"][0]["name"] == "perplexity-deep-research"

    new_content = {
        "clinique": [
            {
                "name": "via-sighup",
                "rationale": "After real SIGHUP",
                "invocation": "auto",
                "priority": 1,
            }
        ],
        "mixte": matrix._data["mixte"],
    }
    tmp_dispatch_yaml.write_text(yaml.safe_dump(new_content), encoding="utf-8")

    # Envoi SIGHUP réel au process
    os.kill(os.getpid(), signal.SIGHUP)
    time.sleep(0.2)  # laisser le handler s'exécuter

    assert matrix._data["clinique"][0]["name"] == "via-sighup"


@pytest.mark.unit
def test_dispatch_yaml_empty_returns_empty_dict(tmp_path):
    """yaml.safe_load(empty file) renvoie None : doit être tolérant (POLYLENS Codex+Gemini P1)."""
    DispatchMatrix.reset()
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    matrix = DispatchMatrix(p)
    assert matrix._data == {}


@pytest.mark.unit
def test_dispatch_yaml_invalid_format_raises(tmp_path):
    """YAML scalaire ou liste = ValueError immédiate (pas AttributeError silencieux)."""
    DispatchMatrix.reset()
    p = tmp_path / "bad.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dispatch matrix invalide"):
        DispatchMatrix(p)


@pytest.mark.unit
def test_dispatch_get_candidates_public_api(tmp_dispatch_yaml):
    """API publique get_candidates() (POLYLENS Kimi P2)."""
    DispatchMatrix.reset()
    matrix = DispatchMatrix.current(path=tmp_dispatch_yaml)
    cands = matrix.get_candidates("clinique")
    assert len(cands) >= 1
    assert all("priority" in c for c in cands)
    # Fallback mixte
    fallback = matrix.get_candidates("inexistant")
    assert len(fallback) >= 1
