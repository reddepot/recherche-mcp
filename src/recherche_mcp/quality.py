"""6 critères qualité — métriques objectivables, sans MIPROv2.

Pondération par domaine via `data/quality_weights.yaml` (cf ADR-0002).
DSPY_GATE: la révision dynamique des poids reste un trigger d'évolution
future (cf decompose.py header).
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np
import yaml

from .models import Domain, GraphEdge, QualityScores, SubQuestion

logger = logging.getLogger("recherche_mcp.quality")

_MODEL = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_MODEL_LOCK = threading.Lock()
_EMBEDDING_AVAILABLE: bool | None = None  # None=untested, True=ok, False=offline


def _try_load_sentence_transformer():
    """Tente de charger sentence-transformers. Return None si offline.

    Cas couverts :
    - ImportError : package non installé
    - OSError : pas de connexion HF Hub + pas de cache local
    - FileNotFoundError : modèle absent du cache offline
    """
    global _EMBEDDING_AVAILABLE
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(_MODEL_NAME)
        _EMBEDDING_AVAILABLE = True
        return model
    except (ImportError, OSError, FileNotFoundError) as exc:
        logger.warning(
            "sentence-transformers indisponible (%s) — fallback Jaccard "
            "tokens activé (graceful degradation offline).",
            type(exc).__name__,
        )
        _EMBEDDING_AVAILABLE = False
        return None


def _embed():
    """Lazy-load thread-safe du modèle d'embeddings.

    Premier appel : ~200MB download. Verrou pour éviter double instanciation.
    Si offline/air-gapped, retourne None → fallback Jaccard.
    """
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                _MODEL = _try_load_sentence_transformer()
    return _MODEL


def set_embed_model(model) -> None:
    """Inject mock model for tests."""
    global _MODEL, _EMBEDDING_AVAILABLE
    with _MODEL_LOCK:
        _MODEL = model
        _EMBEDDING_AVAILABLE = model is not None


def _jaccard_similarity_matrix(texts: list[str]) -> np.ndarray:
    """Fallback Jaccard sur tokens si sentence-transformers indisponible.

    Métrique grossière mais fonctionnelle, qui permet à recherche-mcp de
    tourner sans réseau (environnements air-gapped, CI, etc.).
    """
    token_sets = [set(t.lower().split()) for t in texts]
    n = len(texts)
    sim = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                sim[i][j] = 1.0
            else:
                union = token_sets[i] | token_sets[j]
                inter = token_sets[i] & token_sets[j]
                sim[i][j] = len(inter) / max(len(union), 1)
    return sim


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
    model = _embed()
    if model is not None:
        embs = model.encode(texts, normalize_embeddings=True)
        sim = embs @ embs.T
    else:
        # Fallback Jaccard si embeddings model indisponible (offline)
        sim = _jaccard_similarity_matrix(texts)
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
