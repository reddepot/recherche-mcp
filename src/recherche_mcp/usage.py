"""Log usage permanent du skill /recherche — JSONL append-only.

Objectif : tracer l'usage réel pour Phase A → Phase B data-driven.
Lisible 7+ jours après pour identifier patterns, frictions, améliorations.

Format JSONL : 1 ligne = 1 invocation `decompose_question`.
Rotation mensuelle (`usage_2026-05.jsonl`) pour éviter inflation.

Anti-PII (POLYLENS Q3) :
- Question tronquée à 200 chars + `redact_pii()` appliqué
- Mode `--no-log` côté CLI désactive complètement.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .safety import redact_pii

logger = logging.getLogger("recherche_mcp.usage")

# Path par défaut : ~/Developer/projects/recherche-mcp/runs/
# Override via env var RECHERCHE_MCP_RUNS_DIR (utile pour tests)
DEFAULT_RUNS_DIR = Path.home() / "Developer/projects/recherche-mcp/runs"

_LOCK = threading.Lock()
_DISABLED = False  # contrôlé par CLI --no-log


def disable() -> None:
    """Désactive le logging usage (POLYLENS Q3 mode privacy strict)."""
    global _DISABLED
    _DISABLED = True


def is_enabled() -> bool:
    return not _DISABLED


class UsageEvent(BaseModel):
    """Schéma d'un événement d'usage — append-only JSONL."""

    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    question_excerpt: str = Field(max_length=210)  # 200 + redaction marker margin
    question_length: int
    domain: str | None = None
    strategy: str
    n_subq_requested: int
    n_subq_produced: int
    quality_overall: float
    quality_orthogonalite: float
    quality_couverture: float
    latency_ms: float
    plan_id: str
    error: str | None = None


def _runs_dir() -> Path:
    """Résout le dossier runs (env var override)."""
    override = os.environ.get("RECHERCHE_MCP_RUNS_DIR")
    if override:
        return Path(override)
    return DEFAULT_RUNS_DIR


def _current_log_path() -> Path:
    """Fichier mensuel : `usage_YYYY-MM.jsonl`."""
    now = datetime.now(UTC)
    return _runs_dir() / f"usage_{now.strftime('%Y-%m')}.jsonl"


def log_event(
    *,
    question: str,
    domain: str | None,
    strategy: str,
    n_subq_requested: int,
    plan: Any,
    latency_ms: float,
    error: str | None = None,
) -> None:
    """Append un événement d'usage au log JSONL mensuel.

    Args:
        question: texte original (sera tronqué + PII-redacted).
        domain: hint de domaine (None si auto-détection).
        strategy: "linear" | "graph".
        n_subq_requested: paramètre n_subq de l'appel.
        plan: ResearchPlan produit (peut être None si erreur).
        latency_ms: durée totale décomposition en ms.
        error: message d'erreur si l'appel a échoué (sinon None).

    Best-effort : toute erreur de logging est loggée mais ne propage pas
    (le logging d'usage ne doit jamais casser le pipeline métier).
    """
    if _DISABLED:
        return

    try:
        excerpt = redact_pii(question[:200])
        if len(question) > 200:
            excerpt += "..."

        if plan is not None:
            event = UsageEvent(
                question_excerpt=excerpt,
                question_length=len(question),
                domain=domain,
                strategy=strategy,
                n_subq_requested=n_subq_requested,
                n_subq_produced=len(plan.sub_questions),
                quality_overall=plan.quality.overall,
                quality_orthogonalite=plan.quality.orthogonalite,
                quality_couverture=plan.quality.couverture,
                latency_ms=latency_ms,
                plan_id=str(plan.id),
                error=error,
            )
        else:
            # Erreur : log minimal sans plan
            event = UsageEvent(
                question_excerpt=excerpt,
                question_length=len(question),
                domain=domain,
                strategy=strategy,
                n_subq_requested=n_subq_requested,
                n_subq_produced=0,
                quality_overall=0.0,
                quality_orthogonalite=0.0,
                quality_couverture=0.0,
                latency_ms=latency_ms,
                plan_id="",
                error=error or "unknown",
            )

        log_path = _current_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with _LOCK:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")

    except Exception as exc:  # noqa: BLE001 — best-effort logging
        logger.warning("Failed to log usage event: %s", exc)


def read_events(month: str | None = None) -> list[UsageEvent]:
    """Lit les events d'un mois (ex: '2026-05'). Tous mois si None."""
    runs_dir = _runs_dir()
    if not runs_dir.exists():
        return []

    if month:
        files = [runs_dir / f"usage_{month}.jsonl"]
    else:
        files = sorted(runs_dir.glob("usage_*.jsonl"))

    events = []
    for f in files:
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(UsageEvent.model_validate_json(line))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipping invalid event in %s: %s", f, exc)
    return events
