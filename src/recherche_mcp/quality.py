"""6 critères qualité — métriques objectivables, sans MIPROv2.

DSPY_GATE: la pondération scalaire de ces 6 critères = trigger Phase B.
Phase A v0.3 (audit externe) : pondération par domaine via ADR-0002 +
quality_weights.yaml (Kimi P1 fix).
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import yaml

from .models import Domain, GraphEdge, QualityScores, SubQuestion

_MODEL = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_MODEL_LOCK = threading.Lock()


def _embed():
    """Lazy-load thread-safe du modèle d'embeddings (POLYLENS Gemini P1).

    Premier appel : ~200MB download. Verrou pour éviter double instanciation
    en cas d'appels concurrents (FastMCP gère du parallèle).
    """
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                from sentence_transformers import SentenceTransformer
                _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def set_embed_model(model) -> None:
    """Inject mock model for tests (POLYLENS Codex P1).

    Usage : `set_embed_model(MockEmbedder())` avant les tests pour éviter
    les téléchargements sentence-transformers et accélérer les tests integ.
    """
    global _MODEL
    with _MODEL_LOCK:
        _MODEL = model


_WEIGHTS_PATH = Path(__file__).parent / "data" / "quality_weights.yaml"
_WEIGHTS_CACHE: dict[str, dict[str, float]] | None = None


def get_weights_for_domain(domain: Domain) -> dict[str, float]:
    """Charge les poids des 6 critères pour un domaine (ADR-0002)."""
    global _WEIGHTS_CACHE
    if _WEIGHTS_CACHE is None:
        _WEIGHTS_CACHE = yaml.safe_load(
            _WEIGHTS_PATH.read_text(encoding="utf-8")
        )
    return _WEIGHTS_CACHE.get(domain.value, _WEIGHTS_CACHE["mixte"])


def reset_weights_cache() -> None:
    """Pour tests : reset le cache des poids."""
    global _WEIGHTS_CACHE
    _WEIGHTS_CACHE = None


def score_decomposition(
    subqs: list[SubQuestion],
    edges: list[GraphEdge],
    domain: Domain = Domain.MIXTE,
) -> QualityScores:
    """Calcule les 6 scores qualité d'une décomposition.

    Critères :
    - Couverture : 1 - moyenne similarité hors-diag (proxy hétérogénéité)
    - Orthogonalité : 1 - max similarité hors-diag (overlap > 0.8 = anti-pattern)
    - Autonomie : ratio sous-Q avec rationale > 20 chars
    - Clarté : ratio sous-Q dans sweet spot 8-40 mots
    - Balance : 1 - écart-type relatif des longueurs textuelles
    - Traçabilité : 0.9 si edges présents (graphe), 0.7 sinon (linéaire)
    """
    texts = [s.text for s in subqs]
    embs = _embed().encode(texts, normalize_embeddings=True)
    sim = embs @ embs.T
    np.fill_diagonal(sim, 0.0)
    max_offdiag = float(sim.max())
    mean_offdiag = float(sim.mean())

    orthogonalite = max(0.0, 1.0 - max_offdiag)
    couverture = max(0.0, 1.0 - mean_offdiag)

    lens = np.array([len(t) for t in texts])
    if lens.mean() > 0:
        balance = max(0.0, min(1.0, 1.0 - lens.std() / lens.mean()))
    else:
        balance = 0.0

    autonomie = sum(1 for s in subqs if len(s.rationale) > 20) / len(subqs)
    clarte = sum(1 for t in texts if 8 <= len(t.split()) <= 40) / len(texts)
    tracabilite = 0.9 if edges else 0.7

    return QualityScores(
        couverture=couverture,
        orthogonalite=orthogonalite,
        autonomie=autonomie,
        clarte=clarte,
        balance=balance,
        tracabilite=tracabilite,
        domain=domain,
    )
