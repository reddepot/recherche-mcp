# ADR-0002 — Pondération des critères qualité par domaine

**Date** : 2026-05-09
**Statut** : Accepté (Phase A v0.3, post audit externe 4 voix)
**Référence** : `decision_recherche_skill_devcode_20260508.md` (ADR principal)

## Contexte

L'audit externe 2026-05-09 (Kimi P1, ChatGPT/DeepSeek/Grok implicites) a identifié que `QualityScores.overall` était une moyenne simple non pondérée des 6 critères : couverture, orthogonalité, autonomie, clarté, balance, traçabilité.

Cette équipondération produit une métrique aveugle aux priorités métier :
- Pour le domaine **clinique**, la traçabilité (Loi Kouchner Art. L1110-5 CSP, Art. L4624-8 CT 50 ans) est critique — bien plus que la balance des longueurs textuelles.
- Pour le domaine **juridique_fr**, la couverture (exhaustivité des articles L./R./D. applicables) est primordiale.
- Pour le domaine **technique**, la clarté (code runnable, sans ambiguïté) compte plus que le cadre normatif.

POLYLENS interne avait déjà signalé que la `DSPY_GATE` exigeait « consensus user sur poids des 6 critères » comme l'une des 3 conditions de réveil DSPy. Cet ADR explicite la pondération **avant** Phase B.

## Décision

Pondération par domaine externalisée dans `src/recherche_mcp/data/quality_weights.yaml` :

| Domaine | couverture | orthogonalite | autonomie | clarte | balance | tracabilite |
|---|---|---|---|---|---|---|
| clinique | 0.20 | 0.15 | 0.10 | 0.10 | 0.10 | **0.35** |
| juridique_fr | **0.25** | 0.10 | 0.10 | 0.10 | 0.10 | **0.35** |
| technique | 0.15 | 0.20 | 0.15 | **0.20** | 0.15 | 0.15 |
| multilingue | 0.20 | 0.20 | 0.15 | 0.15 | 0.15 | 0.15 |
| mixte | 0.167 | 0.167 | 0.167 | 0.167 | 0.167 | 0.167 |

### Justifications par domaine

#### Clinique (poids tracabilite=0.35, couverture=0.20)
- Médecin du travail français → contexte médico-légal opposable (Loi Kouchner, Art. L4624-8 conservation 50 ans)
- Traçabilité = source primaire HAS/INRS/SPF citable
- Couverture = pas de risque/limite occulté

#### Juridique_fr (couverture=0.25, tracabilite=0.35)
- Hiérarchie normative stricte (Constitution > traités > Code du travail)
- Articles cités précisément (L./R./D.) avec date version
- Jurisprudence Cass. soc. récente (2024-2026) : traçable obligatoire

#### Technique (clarte=0.20, orthogonalite=0.20)
- Code runnable, versions précises, pas d'ambiguïté = clarté décisive
- Trade-offs orthogonaux entre perf/sécurité/maintenabilité = orthogonalité forte

#### Multilingue (couverture+orthogonalite=0.40)
- Couverture ≥2 langues obligatoire
- Faux-amis terminologiques = orthogonalité critique

#### Mixte (équipondération)
- Backward compatible avec Phase A v0.2 (moyenne simple)
- Domaine non spécialisé : pas de prior métier

## Conséquences

### Positives
- `QualityScores.overall(domain)` produit une métrique alignée objectif métier.
- Lever le blocage DSPY_GATE condition (b) : "consensus user sur poids des 6 critères → métrique scalaire défendable".
- Permet A/B test plus fin : Linear vs Graph par domaine avec poids spécifiques.
- YAML externe = ajustable sans redeploy (cohérent avec dispatch_matrix.yaml).

### Négatives / Risques
- Risque d'overfit : les poids reflètent l'intuition user 2026-05-09, pas une étude empirique.
- Le total user_rating de 30 décompositions notées (DSPY_GATE condition (a)) pourrait suggérer des poids différents.
- Phase B : DEVCODE-Vote sur les poids quand n=30 décompositions disponibles.

### Réversibilité
**Réversible facilement** : changer le YAML ne nécessite ni redeploy ni migration.

## Implémentation

```python
# quality.py
def score_decomposition(
    subqs: list[SubQuestion],
    edges: list[GraphEdge],
    domain: Domain = Domain.MIXTE,
) -> QualityScores:
    ...
    return QualityScores(
        couverture=...,
        ...
        tracabilite=...,
        domain=domain,  # nouveau champ pour overall(domain) computation
    )

# models.py
class QualityScores(BaseModel):
    couverture: float = ...
    ...
    @property
    def overall(self) -> float:
        weights = _load_weights_for_domain(self.domain)
        return sum(weights[k] * getattr(self, k) for k in weights)
```

## Évidence

- Audit externe 2026-05-09 (4 voix) : Kimi P1 explicite, ChatGPT P1 implicite via baseline 0.7 vs 0.5.
- POLYLENS interne CONV-X : DSPY_GATE condition (b) non instrumentée signalée.
- YAML créé : `src/recherche_mcp/data/quality_weights.yaml`.

## Statut DSPY_GATE post-ADR

| Condition | Avant | Après ADR-0002 |
|---|---|---|
| (a) ≥30 décompositions notées ≥0.7 | ❌ Non instrumenté | ❌ encore non instrumenté |
| (b) Consensus user sur poids | ❌ N/A | ✅ ADR-0002 |
| (c) Baseline Linear/Graph stable | ✅ ab_report Phase A | ✅ |

**Verdict** : 2/3 conditions remplies. Reste (a) — collecte log usage Phase A 7+ jours requise.
