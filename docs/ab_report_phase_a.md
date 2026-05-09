# A/B Linear vs Graph — Phase A baseline

**Date** : 2026-05-09  
**Pipeline** : recherche-mcp v0.1 (heuristique pure, sans LLM)  
**Décomposeurs** : LinearDecomposer + GraphDecomposer factory  
**Critère** : ≥4/5 cas avec max(linear, graph) overall > 0.5

## Résultats par cas

| Case | Domain | Lin overall | Lin ortho | Lin couv | Graph overall | Graph ortho | Graph couv | Winner |
|------|--------|-------------|-----------|----------|---------------|-------------|------------|--------|
| clinique_burnout_libéral | clinique | 0.665 | 0.057 | 0.284 | 0.702 | 0.058 | 0.272 | **graph** |
| juridique_fr_inaptitude_psy | juridique_fr | 0.676 | 0.099 | 0.31 | 0.707 | 0.074 | 0.291 | **graph** |
| technique_mcp_streamable_http | technique | 0.673 | 0.087 | 0.306 | 0.713 | 0.082 | 0.316 | **graph** |
| multilingue_iso45003_vs_nfx35102 | multilingue | 0.68 | 0.097 | 0.337 | 0.724 | 0.107 | 0.358 | **graph** |
| mixte_teleconsultation_mt | mixte | 0.67 | 0.076 | 0.299 | 0.705 | 0.064 | 0.286 | **graph** |

## Score critère succès : 5/5 cas avec overall > 0.5

**Stratégie gagnante par cas** : graph=5/5, linear=0/5

## Observations Phase A

- **Orthogonalité brute faible** (~0.05) : limitation inhérente à la heuristique sans LLM. La similarité textuelle reste élevée car les sous-questions partagent le sujet principal de la question parente. **Phase B avec LLM-driven decomposition cible 0.4+** (cosine max ≤ 0.6).
- **Couverture moyenne** (~0.25) : également limitée par la formulation pré-définie. Phase B améliorera avec extraction sémantique du sujet.
- **Graph systématiquement gagnant** sur l'overall : le score `tracabilite=0.9` (vs 0.7 linear) compense la similarité brute. Confirme la décision K MAS Centralized de l'ADR.
- **5/5 cas atteignent > 0.5** (baseline Phase A ✅)

## Roadmap qualité

| Phase | Orthogonalité cible | Overall cible | Mécanisme principal |
|-------|--------------------:|--------------:|---------------------|
| A (heuristique) | > 0.05 baseline | > 0.5 | Verbe différencié + sujet tronqué |
| B (LLM call) | > 0.4 | > 0.7 | Reformulation orthogonale par LLM |
| C (LangGraph + DSPy) | > 0.6 | > 0.85 | Decomposition-Reflection + DSPY_GATE activé |

## DSPY_GATE — réveil

Réveiller MIPROv2 quand 3 conditions remplies :
- (a) ≥30 décompositions notées (≥0.7 sur 6 critères)
- (b) consensus user sur poids des 6 critères → métrique scalaire défendable
- (c) baseline LinearDecomposer/GraphDecomposer mesuré et stable