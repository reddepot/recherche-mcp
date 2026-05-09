"""Décomposeurs Linear / Graph + factory. A/B testable.

DSPY_GATE: réintroduire MIPROv2 quand 3 conditions:
  (a) ≥30 décompositions notées (≥0.7 sur 6 critères)
  (b) consensus user sur poids des 6 critères → métrique scalaire défendable
  (c) baseline LinearDecomposer/GraphDecomposer mesuré et stable

Sinon: NE PAS réveiller. Optionnel = illusion. Trigger = engagement.

Audit externe 2026-05-09 : axes par domaine via `axes_by_domain.yaml`
(4/4 voix unanimes P0 — axes uniformes SST inadaptés aux autres domaines).

Référence ADR : ~/.claude/projects/-Users-radu/memory/decision_recherche_skill_devcode_20260508.md
Décision Phase A : 2026-05-09 (kickoff Opus 4.7).
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from .models import (
    Domain,
    GraphEdge,
    Question,
    ResearchPlan,
    Strategy,
    SubQuestion,
)
from .quality import score_decomposition

# Chargement des axes par domaine depuis YAML versionné
_AXES_PATH = Path(__file__).parent / "data" / "axes_by_domain.yaml"
_AXES_CACHE: dict[str, list[tuple[str, str]]] | None = None
_AXES_LOCK = threading.RLock()


def _load_axes_by_domain() -> dict[str, list[tuple[str, str]]]:
    """Charge `axes_by_domain.yaml` (cache singleton).

    Format YAML : domain → list of {axe_id: verbe}.
    Conversion en list[tuple[axe_id, verbe]] pour préserver l'ordre.
    """
    global _AXES_CACHE
    if _AXES_CACHE is None:
        with _AXES_LOCK:
            if _AXES_CACHE is None:
                raw = yaml.safe_load(_AXES_PATH.read_text(encoding="utf-8"))
                _AXES_CACHE = {
                    domain: [
                        (next(iter(axe.keys())), next(iter(axe.values())))
                        for axe in axes_list
                    ]
                    for domain, axes_list in raw.items()
                }
    return _AXES_CACHE


def get_axes_for_domain(domain: Domain | None) -> list[tuple[str, str]]:
    """Retourne les axes canoniques pour un domaine (fallback "mixte")."""
    domain_key = (domain or Domain.MIXTE).value
    axes = _load_axes_by_domain()
    return axes.get(domain_key, axes["mixte"])


def reset_axes_cache() -> None:
    """Pour tests : reset le cache."""
    global _AXES_CACHE
    with _AXES_LOCK:
        _AXES_CACHE = None


# Compat backward : les tests qui référençaient _CANONICAL_AXES utilisent
# get_axes_for_domain(None) qui retourne mixte (équivalent ancien).
_CANONICAL_AXES = property(lambda self: get_axes_for_domain(None))


def extract_subject(text: str) -> str:
    """Extrait un sujet court (~ 80-120 chars) pour réduire similarité brute.

    Phase A : prend les 120 premiers chars (coupe à un séparateur de mot).
    Phase B : NER + extraction d'entités nommées.

    Module-level pour éviter le couplage fratricide entre LinearDecomposer
    et GraphDecomposer (POLYLENS Gemini+Kimi P2).
    """
    text = text.strip()
    if len(text) <= 120:
        return text
    cut = text[:120].rsplit(" ", 1)[0]
    return f"{cut}..."


class Decomposer(ABC):
    """Interface : produire un ResearchPlan complet à partir d'une Question."""

    @abstractmethod
    def decompose(self, q: Question) -> ResearchPlan: ...


class LinearDecomposer(Decomposer):
    """Décomposition séquentielle: sous-Q indépendantes, ordre non contraignant."""

    def __init__(self, n_subq: int = 5):
        if not 4 <= n_subq <= 7:
            raise ValueError(f"n_subq must be in [4, 7], got {n_subq}")
        self.n_subq = n_subq

    def decompose(self, q: Question) -> ResearchPlan:
        axes = self._select_axes(q.domain, self.n_subq)
        subqs = [self._build_subq(q, axis) for axis in axes]

        from .dispatch import DispatchMatrix
        dispatch = DispatchMatrix.current().resolve(subqs)

        quality = score_decomposition(
            subqs, edges=[], domain=q.domain or Domain.MIXTE
        )

        return ResearchPlan(
            question=q,
            strategy=Strategy.LINEAR,
            sub_questions=subqs,
            edges=[],
            dispatch=dispatch,
            quality=quality,
        )

    def _select_axes(
        self, domain: Domain | None, n: int
    ) -> list[tuple[str, str]]:
        """Sélectionne les axes canoniques du domaine (audit externe P0 fix).

        Audit externe 2026-05-09 : 4/4 voix unanimes — les 7 axes uniformes
        SST étaient appliqués à tous les domaines. Maintenant chargés depuis
        `axes_by_domain.yaml` versionné.
        """
        axes = get_axes_for_domain(domain)
        return axes[:n]

    def _build_subq(self, q: Question, axis: tuple[str, str]) -> SubQuestion:
        # Phase A : heuristique avec verbe différenciant par axe.
        # Phase B : LLM call pour vraie reformulation orthogonale.
        axis_label, axis_verb = axis
        subject = extract_subject(q.text)
        return SubQuestion(
            parent_id=q.id,
            text=f"[{axis_label}] {axis_verb} {subject}",
            rationale=(
                f"Axe canonique « {axis_label} » : {axis_verb}. "
                f"Diversification heuristique Phase A (LLM-driven Phase B)."
            ),
            domain_hint=q.domain or Domain.MIXTE,
            confidence=0.75,
        )


class GraphDecomposer(Decomposer):
    """Décomposition en graphe: sous-Q avec dépendances explicites (DAG).

    Structure : 1 racine "définition" → N branches parallèles → 1 nœud "synthèse".
    Edges : root informs branches, branches depend_on synthesis.
    """

    def __init__(self, n_subq: int = 5):
        if not 4 <= n_subq <= 7:
            raise ValueError(f"n_subq must be in [4, 7], got {n_subq}")
        self.n_subq = n_subq

    def decompose(self, q: Question) -> ResearchPlan:
        domain = q.domain or Domain.MIXTE
        subject = extract_subject(q.text)

        # Phase A v0.3 : axes par domaine (audit externe P0 fix).
        # Structure : 1 root (1er axe = definition/terminologie) + N branches
        # (axes 2..N-1) + 1 synthesis (convergence opérationnelle, non-canonique).
        all_axes = get_axes_for_domain(domain)
        root_axis = all_axes[0]
        branch_axes = all_axes[1:]

        root_label, root_verb = root_axis
        root = SubQuestion(
            parent_id=q.id,
            text=f"[{root_label}] {root_verb} {subject}",
            rationale="Racine: cadrage initial préalable aux axes orthogonaux.",
            domain_hint=domain,
            confidence=0.85,
        )

        # n_branches = n_subq - 2 (1 root + N branches + 1 synthesis)
        n_branches = self.n_subq - 2
        branches = [
            SubQuestion(
                parent_id=q.id,
                text=f"[{label}] {verb} {subject}",
                rationale=f"Branche orthogonale « {label} » (perspective complémentaire).",
                domain_hint=domain,
                confidence=0.75,
            )
            for (label, verb) in branch_axes[:n_branches]
        ]

        synthesis = SubQuestion(
            parent_id=q.id,
            text=f"[synthèse] Intégrer en synthèse opérationnelle les axes étudiés sur {subject}",
            rationale="Convergence opérationnelle : intégration des branches.",
            domain_hint=domain,
            confidence=0.70,
        )

        subqs = [root, *branches, synthesis]

        edges = (
            [
                GraphEdge(source_id=root.id, target_id=b.id, relation="informs")
                for b in branches
            ]
            + [
                GraphEdge(
                    source_id=b.id, target_id=synthesis.id, relation="depends_on"
                )
                for b in branches
            ]
        )

        from .dispatch import DispatchMatrix
        dispatch = DispatchMatrix.current().resolve(subqs)

        quality = score_decomposition(subqs, edges=edges, domain=domain)

        return ResearchPlan(
            question=q,
            strategy=Strategy.GRAPH,
            sub_questions=subqs,
            edges=edges,
            dispatch=dispatch,
            quality=quality,
        )


def make_decomposer(strategy: Strategy, n_subq: int = 5) -> Decomposer:
    """Factory — point unique pour A/B test Linear vs Graph.

    Audit externe 2026-05-09 : `case _: raise` ajouté pour détecter
    immédiatement toute Strategy ajoutée (Phase B : HYBRID, etc.) qui
    n'aurait pas son décomposeur correspondant.
    """
    match strategy:
        case Strategy.LINEAR:
            return LinearDecomposer(n_subq)
        case Strategy.GRAPH:
            return GraphDecomposer(n_subq)
        case _:
            raise ValueError(f"Unsupported strategy: {strategy!r}")
