"""Entrypoint FastMCP — stdio transport uniquement (Phase A).

Décision architecturale : pas de Streamable HTTP en LAN-only (sur-engineering
selon Kimi+GLM, ADR 2026-05-08). HTTP transport sera réservé à Phase B Sprint 5
pour binding distant avec OAuth+mTLS.
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

import click
from fastmcp import FastMCP

from .decompose import make_decomposer
from .dispatch import DispatchMatrix
from .models import Domain, Question, ResearchPlan, Strategy
from .prompts.render import render_subprompts
from .safety import has_potential_pii, redact_pii

logger = logging.getLogger("recherche_mcp")

mcp = FastMCP(
    name="recherche",
    instructions=(
        "Décomposition orthogonale de questions de recherche en 4-6 sous-prompts "
        "experts par domaine, avec annonce de matrice dispatch. Phase A : pas "
        "d'auto API DR ; le skill paste manuel. Strategy linear|graph A/B testable."
    ),
)


@mcp.tool()
def decompose_question(
    text: str,
    domain: Literal[
        "clinique", "juridique_fr", "technique", "multilingue", "mixte"
    ]
    | None = None,
    strategy: Literal["linear", "graph"] = "linear",
    n_subq: int = 5,
) -> dict:
    """Décompose une question en 4-6 sous-questions orthogonales.

    Args:
        text: la question à décomposer (10-4000 caractères).
        domain: hint de domaine. Phase A : si None, fallback "mixte"
            (auto-détection LLM = Phase B).
        strategy: linear (séquentiel, sous-Q indépendantes) ou
            graph (DAG avec dépendances explicites).
        n_subq: nombre de sous-questions, 4-7 (défaut 5).

    Returns:
        ResearchPlan complet (sub_questions + edges + dispatch + quality)
        sérialisé en dict JSON-compatible.
    """
    if has_potential_pii(text):
        logger.warning(
            "PII patterns detected in question — text will be redacted in logs"
        )
    domain_enum = Domain(domain) if domain else None
    q = Question(text=text, domain=domain_enum)
    plan = make_decomposer(Strategy(strategy), n_subq=n_subq).decompose(q)
    return plan.model_dump(mode="json")


@mcp.tool()
def generate_subprompts(plan_json: dict) -> list[dict]:
    """Rend les sous-prompts experts via templates Jinja2 par domaine.

    Args:
        plan_json: ResearchPlan sérialisé (sortie de decompose_question).

    Returns:
        Liste de dicts {sub_question_id, prompt} prêts à copier-coller
        vers les modèles candidats annoncés par dispatch.
    """
    plan = ResearchPlan.model_validate(plan_json)
    return render_subprompts(plan)


@mcp.tool()
def catalog_sources(
    domain: Literal[
        "clinique", "juridique_fr", "technique", "multilingue", "mixte"
    ] = "mixte",
) -> list[dict]:
    """Retourne les modèles candidats pour un domaine, ordonnés par priorité.

    Args:
        domain: domaine cible. Si non reconnu, fallback "mixte".

    Returns:
        Liste de dicts {name, rationale, invocation, priority}.
    """
    matrix = DispatchMatrix.current()
    cands = matrix._data.get(domain, matrix._data.get("mixte", []))
    return sorted(cands, key=lambda c: c.get("priority", 99))


@click.command()
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio"]),
    help="Phase A : stdio uniquement.",
)
@click.option(
    "--no-log",
    is_flag=True,
    default=False,
    help="Désactive complètement les logs (mode privacy strict, Q3 user).",
)
@click.option(
    "--log-level",
    default="WARNING",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Niveau de log. Défaut WARNING (anti-PII).",
)
def main(transport: str, no_log: bool, log_level: str):
    """Lance le serveur MCP recherche-mcp."""
    if no_log:
        logging.disable(logging.CRITICAL)
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,  # stdout est réservé au protocole MCP
        )
        # Filtre PII sur tous les records produits par recherche_mcp.*
        for handler in logging.getLogger().handlers:
            handler.addFilter(_PIIRedactFilter())
    mcp.run(transport=transport)


class _PIIRedactFilter(logging.Filter):
    """Filtre PII appliqué aux logs (Q3 décision user 2026-05-09)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_pii(record.msg)
        if record.args:
            record.args = tuple(
                redact_pii(a) if isinstance(a, str) else a for a in record.args
            )
        return True


if __name__ == "__main__":
    main()
