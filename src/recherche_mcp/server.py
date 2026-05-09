"""Entrypoint serveur MCP — stdio transport uniquement (Phase A).

Décision architecturale : pas de Streamable HTTP en LAN-only (sur-engineering).
HTTP transport sera ajouté Phase B/C avec OAuth+mTLS pour binding distant.

L'enregistrement des outils passe EXCLUSIVEMENT par `_adapter.register_tool()`
via la façade `MCPServerPort` — aucun import direct de FastMCP dans le code
métier (port hexagonal pour découpler du SDK).
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Literal

import click

from . import usage
from .decompose import make_decomposer
from .dispatch import DispatchMatrix
from .models import Domain, Question, ResearchPlan, Strategy
from .port import FastMCPAdapter
from .prompts.render import render_subprompts
from .safety import has_potential_pii, redact_pii

logger = logging.getLogger("recherche_mcp")


# ============================================================================
# Tool implementations (Python pures, indépendantes du SDK MCP)
# ============================================================================

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

    t0 = time.perf_counter()
    plan = None
    error: str | None = None
    try:
        plan = make_decomposer(Strategy(strategy), n_subq=n_subq).decompose(q)
        return plan.model_dump(mode="json")
    except (ValueError, RuntimeError) as exc:
        # Erreurs métier typées (validation Pydantic, dispatch invalide, etc.).
        # Tout autre type d'exception remonte non-capturé.
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000
        usage.log_event(
            question=text,
            domain=domain,
            strategy=strategy,
            n_subq_requested=n_subq,
            plan=plan,
            latency_ms=latency_ms,
            error=error,
        )


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
    return DispatchMatrix.current().get_candidates(domain)


# ============================================================================
# Adapter MCP : injection des tools via la façade (PAS de @mcp.tool() direct)
# ============================================================================

def build_adapter() -> FastMCPAdapter:
    """Construit l'adapter MCP et y enregistre les 3 outils via le Port.

    Aucune dépendance directe à FastMCP dans le code métier : un swap vers
    un autre SDK MCP ne nécessite de modifier que `FastMCPAdapter`.
    """
    adapter = FastMCPAdapter(
        name="recherche",
        instructions=(
            "Décomposition orthogonale de questions de recherche en 4-6 "
            "sous-prompts experts par domaine, avec annonce de matrice "
            "dispatch. Phase A : pas d'auto API DR ; le skill paste manuel. "
            "Strategy linear|graph A/B testable."
        ),
    )
    adapter.register_tool(
        "decompose_question",
        decompose_question,
        description=decompose_question.__doc__ or "",
    )
    adapter.register_tool(
        "generate_subprompts",
        generate_subprompts,
        description=generate_subprompts.__doc__ or "",
    )
    adapter.register_tool(
        "catalog_sources",
        catalog_sources,
        description=catalog_sources.__doc__ or "",
    )
    return adapter


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
    help="Désactive complètement les logs (mode privacy strict).",
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
        usage.disable()
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stderr,  # stdout est réservé au protocole MCP
        )
        # Filter racine + Formatter combinés pour couvrir aussi les handlers
        # ajoutés ultérieurement par bibliothèques tierces.
        root = logging.getLogger()
        root.addFilter(_PIIRedactFilter())
        for handler in root.handlers:
            handler.setFormatter(_PIIRedactFormatter(handler.formatter))

    adapter = build_adapter()
    adapter.run(transport=transport)


class _PIIRedactFormatter(logging.Formatter):
    """Formatter qui caviarde les PII dans le message final.

    Combiné avec `_PIIRedactFilter` au niveau racine pour couvrir aussi
    les handlers ajoutés par bibliothèques tierces (sentence-transformers,
    fastmcp). Idempotent grâce aux markers `[REDACTED-*]`.
    """

    def __init__(self, base: logging.Formatter | None = None):
        self._base = base or logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        rendered = self._base.format(record)
        return redact_pii(rendered)


class _PIIRedactFilter(logging.Filter):
    """Filter racine qui caviarde les PII dans `record.msg` avant tout handler.

    Un Formatter sur les handlers existants ne couvre pas ceux ajoutés
    ultérieurement par d'autres bibliothèques. Ce Filter au niveau racine
    garantit la rédaction sur l'ensemble du logging.
    """

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
