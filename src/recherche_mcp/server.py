"""Entrypoint serveur MCP — stdio transport uniquement (Phase A).

Décision architecturale : pas de Streamable HTTP en LAN-only (sur-engineering
selon Kimi+GLM, ADR 2026-05-08). HTTP transport sera réservé à Phase B Sprint 5
pour binding distant avec OAuth+mTLS.

Audit externe 2026-05-09 (4 voix unanimes P0) : abstraction `MCPServerPort`
était bypassée par `.native`. Cette version utilise EXCLUSIVEMENT
`_adapter.register_tool()`. Le code métier ne touche plus FastMCP directement.
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
        # Audit externe 2026-05-09 Grok P1 : exceptions typées au lieu de
        # broad except Exception. Erreurs métier explicites.
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

    Audit externe 2026-05-09 : aucune dépendance directe à FastMCP dans le
    code métier. Si on veut swap vers SDK officiel mcp 1.x, seul cet appel
    + l'implémentation de FastMCPAdapter changent.
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
        # Filter racine + Formatter combinés pour couvrir handlers tiers
        # (audit externe 2026-05-09 ChatGPT P1).
        root = logging.getLogger()
        root.addFilter(_PIIRedactFilter())
        for handler in root.handlers:
            handler.setFormatter(_PIIRedactFormatter(handler.formatter))

    adapter = build_adapter()
    adapter.run(transport=transport)


class _PIIRedactFormatter(logging.Formatter):
    """Formatter qui caviarde les PII dans le message final.

    Audit externe 2026-05-09 : combiné avec _PIIRedactFilter au niveau racine
    pour couvrir handlers ajoutés par bibliothèques tierces (sentence-transformers,
    fastmcp). Idempotent grâce à `[REDACTED-*]` markers.
    """

    def __init__(self, base: logging.Formatter | None = None):
        self._base = base or logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        rendered = self._base.format(record)
        return redact_pii(rendered)


class _PIIRedactFilter(logging.Filter):
    """Filter racine qui redige PII dans record.msg avant tout handler.

    Audit externe 2026-05-09 ChatGPT P1 : Formatter sur handlers existants
    seulement ne couvre pas les handlers ajoutés ultérieurement. Ce Filter
    racine garantit la rédaction même pour handlers tiers.
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
