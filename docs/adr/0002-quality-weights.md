# ADR-0002 — Pondération des critères qualité par domaine

**Date** : 2026-05-09
**Statut** : Accepté
**Référence** : ADR principal du projet (mémoire utilisateur).

## Contexte

`QualityScores.overall` calculait initialement une moyenne simple non pondérée des 6 critères : couverture, orthogonalité, autonomie, clarté, balance, traçabilité.

Cette équipondération produit une métrique aveugle aux priorités métier :
- Pour le domaine **clinique**, la traçabilité (Loi Kouchner Art. L1110-5 CSP, Art. L4624-8 CT 50 ans) est critique — bien plus que la balance des longueurs textuelles.
- Pour le domaine **juridique_fr**, la couverture (exhaustivité des articles L./R./D. applicables) est primordiale.
- Pour le domaine **technique**, la clarté (code runnable, sans ambiguïté) compte plus que le cadre normatif.

La gate `DSPY_GATE` (cf `decompose.py`) exige notamment un « consensus sur les poids des 6 critères » comme l'une des trois conditions de réveil de MIPROv2. Cet ADR explicite cette pondération **avant** Phase B.

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
- Le profil `mixte` reste équipondéré (équivalent moyenne simple) pour les questions sans domaine spécifique
- Domaine non spécialisé : pas de prior métier

## Conséquences

### Positives
- `QualityScores.overall(domain)` produit une métrique alignée objectif métier.
- Lever le blocage DSPY_GATE condition (b) : "consensus user sur poids des 6 critères → métrique scalaire défendable".
- Permet A/B test plus fin : Linear vs Graph par domaine avec poids spécifiques.
- YAML externe = ajustable sans redeploy (cohérent avec dispatch_matrix.yaml).

### Négatives / Risques
- Risque d'overfit : les poids reflètent l'intuition initiale du designer, pas une étude empirique.
- Le retour de N décompositions notées peut suggérer des poids différents (cf DSPY_GATE).
- Une délibération formalisée sur les poids (DEVCODE-Vote) sera utile une fois ≥30 décompositions disponibles.

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

- YAML créé : `src/recherche_mcp/data/quality_weights.yaml`.
- Implémentation : `quality.get_weights_for_domain()` + `models.QualityScores.overall` lazy.

## Statut DSPY_GATE après cet ADR

| Condition | Statut |
|---|---|
| (a) ≥30 décompositions notées avec scores ≥ 0.7 | À mesurer (collecte logs usage en cours) |
| (b) Consensus sur poids des 6 critères | ✅ Acté par cet ADR |
| (c) Baseline Linear/Graph stable | ✅ `docs/ab_report_phase_a.md` |

Reste donc à instrumenter et collecter (a) avant de réveiller MIPROv2.
