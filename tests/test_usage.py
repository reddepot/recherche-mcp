"""Tests log usage permanent (Phase A v0.2 — feature itération Phase B)."""

from __future__ import annotations

import json
import os

import pytest

from recherche_mcp import usage
from recherche_mcp.decompose import LinearDecomposer
from recherche_mcp.models import Domain, Question


@pytest.fixture(autouse=True)
def isolated_runs_dir(tmp_path, monkeypatch):
    """Isole chaque test dans un runs_dir éphémère."""
    monkeypatch.setenv("RECHERCHE_MCP_RUNS_DIR", str(tmp_path / "runs"))
    # Reset disabled flag entre tests
    usage._DISABLED = False
    yield


@pytest.mark.integ
def test_log_event_basic(question_clinique, tmp_path):
    plan = LinearDecomposer().decompose(question_clinique)
    usage.log_event(
        question=question_clinique.text,
        domain="clinique",
        strategy="linear",
        n_subq_requested=5,
        plan=plan,
        latency_ms=42.5,
    )
    events = usage.read_events()
    assert len(events) == 1
    e = events[0]
    assert e.domain == "clinique"
    assert e.strategy == "linear"
    assert e.n_subq_produced == 5
    assert e.latency_ms == 42.5
    assert e.error is None
    assert "burnout" in e.question_excerpt.lower()


@pytest.mark.unit
def test_log_event_disabled():
    usage.disable()
    usage.log_event(
        question="x" * 50,
        domain="clinique",
        strategy="linear",
        n_subq_requested=5,
        plan=None,
        latency_ms=1.0,
    )
    assert usage.read_events() == []


@pytest.mark.unit
def test_log_event_redacts_pii():
    """La question loguée ne doit PAS contenir les PII bruts."""
    text = (
        "Salarié 1 85 04 75 114 080 12 né le 15/03/1985, "
        "tel 0612345678, mail test@example.com, burnout 2024"
    )
    usage.log_event(
        question=text,
        domain="clinique",
        strategy="linear",
        n_subq_requested=5,
        plan=None,
        latency_ms=1.0,
        error="test",
    )
    events = usage.read_events()
    assert len(events) == 1
    excerpt = events[0].question_excerpt
    assert "1 85 04 75 114 080 12" not in excerpt
    assert "0612345678" not in excerpt
    assert "test@example.com" not in excerpt
    assert "[REDACTED-NIR]" in excerpt or "[REDACTED-DATE]" in excerpt


@pytest.mark.unit
def test_log_event_truncates_long_questions():
    long_q = "x" * 5000
    usage.log_event(
        question=long_q,
        domain=None,
        strategy="graph",
        n_subq_requested=5,
        plan=None,
        latency_ms=1.0,
        error="too long",
    )
    events = usage.read_events()
    assert len(events) == 1
    # Excerpt = 200 chars + "..." = 203 chars max (avant redact)
    assert len(events[0].question_excerpt) <= 210
    assert events[0].question_length == 5000


@pytest.mark.unit
def test_log_event_error_path():
    usage.log_event(
        question="x" * 50,
        domain="technique",
        strategy="linear",
        n_subq_requested=5,
        plan=None,  # erreur, pas de plan
        latency_ms=10.0,
        error="ValidationError: bad input",
    )
    events = usage.read_events()
    assert len(events) == 1
    e = events[0]
    assert e.error == "ValidationError: bad input"
    assert e.n_subq_produced == 0
    assert e.quality_overall == 0.0


@pytest.mark.integ
def test_log_event_appends_jsonl(question_clinique, tmp_path):
    """Plusieurs events s'append correctement."""
    plan = LinearDecomposer().decompose(question_clinique)
    for _ in range(3):
        usage.log_event(
            question=question_clinique.text,
            domain="clinique",
            strategy="linear",
            n_subq_requested=5,
            plan=plan,
            latency_ms=10.0,
        )
    events = usage.read_events()
    assert len(events) == 3


@pytest.mark.unit
def test_log_event_best_effort_on_io_failure(monkeypatch, tmp_path):
    """Une erreur de logging ne doit jamais propager au caller."""
    # Pointe RUNS_DIR vers un chemin impossible
    monkeypatch.setenv("RECHERCHE_MCP_RUNS_DIR", "/nonexistent/forbidden/path/xyz")
    # Ne raise pas
    usage.log_event(
        question="x" * 50,
        domain="clinique",
        strategy="linear",
        n_subq_requested=5,
        plan=None,
        latency_ms=1.0,
        error="test",
    )
