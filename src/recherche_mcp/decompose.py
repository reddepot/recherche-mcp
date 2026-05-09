"""Décomposeurs Linear / Graph + factory. A/B testable.

DSPY_GATE: réintroduire MIPROv2 quand 3 conditions:
  (a) ≥30 décompositions notées (≥0.7 sur 6 critères)
  (b) consensus user sur poids des 6 critères → métrique scalaire défendable
  (c) baseline LinearDecomposer/GraphDecomposer mesuré et stable

Sinon: NE PAS réveiller. Optionnel = illusion. Trigger = engagement.

Référence ADR : ~/.claude/projects/-Users-radu/memory/decision_recherche_skill_devcode_20260508.md
Décision Phase A : 2026-05-09 (kickoff Opus 4.7).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    Domain,
    GraphEdge,
    Question,
    ResearchPlan,
    Strategy,
    SubQuestion,
)
from .quality import score_decomposition

# 7 axes canoniques pour décomposition orthogonale (validés par convergence
# 5 voix Prompt C : Decomposition-Reflection Xiao 2025, Anthropic Claude
# Research, ReAgent, Workforce NeurIPS 2025, AOP Meta FAIR 2026)
#
# Chaque axe a un verbe différenciant pour réduire la similarité textuelle
# brute entre sous-questions (limitation Phase A heuristique : sans LLM call,
# la diversité vient uniquement de la formulation imposée par axe).
_CANONICAL_AXES: list[tuple[str, str]] = [
    ("definition", "Définir précisément les concepts et terminologie de"),
    ("etat_art", "Synthétiser l'état de l'art empirique 2024-2026 sur"),
    ("cadre_normatif", "Identifier le cadre normatif applicable (lois, normes, recommandations) à"),
    ("praticien_cible", "Préciser la portée pratique pour le praticien cible concernant"),
    ("risques_limites", "Cartographier les risques, limites et controverses autour de"),
    ("operationnalisation", "Décrire l'opérationnalisation concrète (outils, protocoles, indicateurs) de"),
    ("comparaison_int", "Comparer avec les pratiques internationales équivalentes pour"),
]


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

        # Lazy import pour éviter circular (DispatchMatrix peut importer models)
        from .dispatch import DispatchMatrix
        dispatch = DispatchMatrix.current().resolve(subqs)

        quality = score_decomposition(subqs, edges=[])

        return ResearchPlan(
            question=q,
            strategy=Strategy.LINEAR,
            sub_questions=subqs,
            edges=[],
            dispatch=dispatch,
            quality=quality,
        )

    def _select_axes(self, domain: Domain | None, n: int) -> list[tuple[str, str]]:
        return _CANONICAL_AXES[:n]

    def _build_subq(self, q: Question, axis: tuple[str, str]) -> SubQuestion:
        # Phase A : heuristique avec verbe différenciant par axe.
        # Phase B : LLM call pour vraie reformulation orthogonale.
        axis_label, axis_verb = axis
        # Tronque la question parente à son sujet principal (évite duplication
        # du texte intégral qui plombe l'orthogonalité)
        subject = self._extract_subject(q.text)
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

    @staticmethod
    def _extract_subject(text: str) -> str:
        """Extrait un sujet court (~ 80-120 chars) pour réduire similarité brute.

        Heuristique simple Phase A : prend les 100 premiers chars + "..." si tronqué.
        Phase B : NER + extraction d'entités nommées.
        """
        text = text.strip()
        if len(text) <= 120:
            return text
        # Coupe à un séparateur de mot
        cut = text[:120].rsplit(" ", 1)[0]
        return f"{cut}..."


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
        subject = LinearDecomposer._extract_subject(q.text)

        root = SubQuestion(
            parent_id=q.id,
            text=f"[définition] Définir précisément les concepts et terminologie de {subject}",
            rationale="Racine: cadrage terminologique préalable aux axes.",
            domain_hint=domain,
            confidence=0.85,
        )

        # n_subq = 1 root + (n_subq - 2) branches + 1 synthesis
        # Utilise les axes canoniques différenciants (sans definition ni synthèse)
        branch_axes = [
            ("etat_art", "Synthétiser l'état de l'art empirique 2024-2026 sur"),
            ("cadre_normatif", "Identifier le cadre normatif applicable à"),
            ("risques_limites", "Cartographier les risques et limites de"),
            ("operationnalisation", "Décrire l'opérationnalisation concrète de"),
            ("comparaison_int", "Comparer avec pratiques internationales pour"),
        ]
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

        quality = score_decomposition(subqs, edges=edges)

        return ResearchPlan(
            question=q,
            strategy=Strategy.GRAPH,
            sub_questions=subqs,
            edges=edges,
            dispatch=dispatch,
            quality=quality,
        )


def make_decomposer(strategy: Strategy, n_subq: int = 5) -> Decomposer:
    """Factory — point unique pour A/B test Linear vs Graph."""
    match strategy:
        case Strategy.LINEAR:
            return LinearDecomposer(n_subq)
        case Strategy.GRAPH:
            return GraphDecomposer(n_subq)
