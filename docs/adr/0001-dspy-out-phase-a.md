# ADR-0001 — DSPy MIPROv2 OUT pour Phase A (DSPY_GATE)

**Date** : 2026-05-09
**Statut** : Accepté
**Référence** : ADR global du projet (mémoire utilisateur).

## Contexte

Le DEVCODE-Vote P0 (13 voix initiales + 4 voix challenge) sur la conception du skill `/recherche` a placé DSPy MIPROv2 en option Sprint 5. La voix Kimi K2.6 a explicitement signalé l'anti-pattern « optionnel = illusion » : intégrer DSPy après que tous les prompts sont hardcodés dans LangGraph forcerait une réécriture massive.

User a tranché 2026-05-09 : la décision DSPy doit être **binaire** dès Sprint 1, pas optionnelle plus tard.

## Décision

**MIPROv2 N'ENTRE PAS dans Phase A.**

Trigger explicite (`DSPY_GATE`) inscrit en commentaire dans `src/recherche_mcp/decompose.py` :

```python
# DSPY_GATE: réintroduire MIPROv2 quand 3 conditions:
#   (a) ≥30 décompositions notées (≥0.7 sur 6 critères)
#   (b) consensus user sur poids des 6 critères → métrique scalaire défendable
#   (c) baseline LinearDecomposer/GraphDecomposer mesuré et stable
# Sinon: NE PAS réveiller. Optionnel = illusion. Trigger = engagement.
```

## Justification (3 raisons)

### 1. Bootstrap problem — corpus d'entraînement manquant

MIPROv2 fait du Bayesian Optimization sur (instructions × few-shots) avec auto=light/medium/heavy. La doc officielle ([dspy.ai/api/optimizers/MIPROv2](https://dspy.ai/api/optimizers/MIPROv2/)) et le tutoriel Langtrace ([langtrace.ai/blog/grokking-miprov2](https://www.langtrace.ai/blog/grokking-miprov2-the-new-optimizer-from-dspy)) convergent : il faut **≥50 exemples labellisés** avec métrique scalaire pour que la BO converge.

User a 5 cas de test cibles (`tests/fixtures/cases.yaml`). Rapport 1:10. L'optimisation surapprendrait massivement et produirait un prompt hyper-spécifique qui dégraderait la généralisation hors-corpus.

### 2. Métrique scalaire incompatible avec critères multi-axes

Le pattern décomposition orthogonale repose sur **6 critères qualité** :
- Couverture
- Orthogonalité
- Autonomie
- Clarté
- Balance
- Traçabilité

MIPROv2 exige une `metric: Callable[[Example, Prediction], float]` retournant un scalaire. Composer 6 critères en une fonction scalaire pondérée = choisir arbitrairement les poids = optimiser un proxy biaisé. Tant que le user n'a pas observé 30+ décompositions réelles et formé une intuition sur les arbitrages, fixer les poids prématurément verrouille la mauvaise objective.

### 3. Phase A = formalisation, pas optimisation

Iternal RAG frameworks comparison 2026 : *"DSPy comes with a learning curve and limited production tooling. Most teams pair it with other systems once models move beyond experimentation."*

Phase A EST l'expérimentation. Importer la complexité opérationnelle DSPy (Optuna en `dspy[optuna]` extras, runtime BO, traces, cache de bootstrapping) avant d'avoir un baseline = inversion d'ordre canonique.

**Mesure d'abord, optimise ensuite.**

## Conditions de réveil (DSPY_GATE)

Les 3 conditions sont cumulatives — toutes doivent être remplies :

| Condition | Comment vérifier |
|-----------|-----------------|
| (a) ≥30 décompositions notées avec score ≥ 0.7 sur les 6 critères | Hub de runs : `~/Developer/projects/recherche-mcp/runs/<date>_<slug>/quality.json` agrégé. |
| (b) Consensus user sur poids des 6 critères → métrique scalaire défendable | ADR explicite `0002-quality-weights.md` à créer Phase B. |
| (c) Baseline LinearDecomposer/GraphDecomposer mesuré et stable | `docs/ab_report_phase_a.md` + 3+ runs ultérieurs montrant variance < 10%. |

Si l'une des 3 manque : **NE PAS réveiller MIPROv2**. Préférer une heuristique enrichie ou un appel LLM direct.

## Alternatives considérées

- **Inclure DSPy dès Sprint 1** : rejeté car bootstrap impossible (5 exemples).
- **DSPy GEPA (Reflective Prompt Optimizer)** : potentiellement plus aligné avec critères multi-axes via reflection. À comparer à MIPROv2 quand le trigger sera atteint. Référence : [dspy.ai/api/optimizers/GEPA/overview](https://dspy.ai/api/optimizers/GEPA/overview/).
- **Optimiser via évolution génétique custom** : rejeté car réinvention de roue, pas dans le périmètre Phase A.

## Conséquences

### Positives

- Phase A reste légère (8-12 j-h vs 20+ avec DSPy).
- Pipeline mesurable et auditable dès v0.1.
- Évite le piège du « optionnel devenu jamais ».
- Critères de réveil engageants : on saura précisément quand activer.

### Négatives / Risques

- Heuristique pure produit des scores qualité limités (orthogonalité ~0.05, overall ~0.66) — documenté dans `ab_report_phase_a.md`.
- Si user veut « optimiser » avant Phase B, ce sera frustrant.
- Risque que les 3 conditions ne soient jamais toutes remplies → DSPy abandonné de fait. Acceptable si la Phase B/C autres techniques (LLM-driven, LangGraph) suffisent.

## Statut Phase A actuel

- 35/35 tests verts.
- ab_report_phase_a.md généré : 5/5 cas atteignent overall > 0.5 (baseline Phase A).
- DSPY_GATE inscrit en commentaire `decompose.py`.
- Aucun import DSPy dans `pyproject.toml`.
