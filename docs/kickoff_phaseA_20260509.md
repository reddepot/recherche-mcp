# Kickoff Phase A — Skill `/recherche` v0.1 (Voie 3 minimal)

**Date** : 2026-05-09, 05h02 Paris
**Modèle générateur** : Claude Opus 4.7 (routine remote `trig_01L2DLJzpDVJo5cAmGqTEeA1`)
**Durée prévue** : 8-12 j-h
**ADR référence** : `~/.claude/projects/-Users-radu/memory/decision_recherche_skill_devcode_20260508.md`
**Statut** : Décisions D / E / H' / K validées par DEVCODE-Vote (13+4 voix). Phase A implémente D + amorce H' uniquement.

---

## 1. Pré-vol — Décision binaire DSPy MIPROv2 : **OUT pour Phase A**

### Verdict tranché

**MIPROv2 N'ENTRE PAS dans Phase A.** Il est explicitement réinscrit comme **trigger conditionnel Phase B**, pas "optionnel Sprint 5". La condition de réveil est inscrite dans le code (commentaire `# DSPY_GATE` dans `decompose.py`).

### 3 raisons précises

1. **Bootstrap problem — corpus d'entraînement manquant.** MIPROv2 fait du Bayesian Optimization sur (instructions × few-shots) avec auto=light/medium/heavy. La doc officielle ([dspy.ai/api/optimizers/MIPROv2](https://dspy.ai/api/optimizers/MIPROv2/)) et le tutoriel Langtrace ([langtrace.ai/blog/grokking-miprov2](https://www.langtrace.ai/blog/grokking-miprov2-the-new-optimizer-from-dspy)) convergent : il faut **≥50 exemples labellisés** avec métrique scalaire pour que la BO converge. Le user a 5 cas de test cibles. Rapport 1:10. L'optimisation surapprendrait massivement sur 5 points et produirait un prompt hyper-spécifique qui dégraderait la généralisation hors-corpus. C'est documenté chez Towards Data Science ([systematic-llm-prompt-engineering-using-dspy-optimization](https://towardsdatascience.com/systematic-llm-prompt-engineering-using-dspy-optimization/)) comme l'erreur n°1 d'adoption.

2. **Métrique scalaire incompatible avec critères multi-axes.** Le pattern décomposition orthogonale repose sur **6 critères qualité** (Couverture, Orthogonalité, Autonomie, Clarté, Balance, Traçabilité). MIPROv2 exige une `metric: Callable[[Example, Prediction], float]` retournant un scalaire. Composer 6 critères en une fonction scalaire pondérée = choisir arbitrairement les poids = optimiser un proxy biaisé. Tant que le user n'a pas observé 30+ décompositions réelles et formé une intuition sur les arbitrages entre critères, fixer les poids prématurément verrouille la mauvaise objective.

3. **Phase A = formalisation, pas optimisation.** L'analyse industrie 2026 ([Iternal RAG frameworks comparison](https://iternal.ai/blockify-rag-frameworks)) le dit explicitement : *"DSPy comes with a learning curve and limited production tooling. Most teams pair it with other systems once models move beyond experimentation."* Phase A EST l'expérimentation. Importer la complexité opérationnelle DSPy avant d'avoir un baseline = inversion d'ordre canonique. **Mesure d'abord, optimise ensuite.**

### Trigger de réveil DSPy (Phase B)

```python
# decompose.py — commentaire explicite
# DSPY_GATE: réintroduire MIPROv2 quand 3 conditions:
#   (a) ≥30 décompositions notées (≥0.7 sur 6 critères)
#   (b) consensus user sur poids des 6 critères → métrique scalaire défendable
#   (c) baseline LinearDecomposer/GraphDecomposer mesuré et stable
# Sinon: NE PAS réveiller. Optionnel = illusion. Trigger = engagement.
```

---

## Décisions user (2026-05-09, validation kickoff)

| Q | Décision | Justification |
|---|---|---|
| **Q1** DSPy OUT Phase A | ✅ OUI | 3 raisons solides ; gate explicite |
| **Q2** Repo | ✅ Gitea NAS | Cohérent écosystème user, privacy by default |
| **Q3** Logging anti-PII | ✅ OUI (a regex + b `--no-log`) | Cas cliniques = données santé, baseline RGPD |
| **Q4** Seuil orthogonalité | ✅ 0.2 baseline → mesurer | Approche empirique cohérente Phase A |
| **Q5** Auto-détection domaine | ✅ Reporter Phase B | Skill demande explicitement, simplicité v0.1 |

---

## Plan jour par jour

| Jour | Demi-journée | Objectif | Commit |
|---|---|---|---|
| **J1** | matin | Bootstrap repo + scaffolding minimal | `chore: bootstrap recherche-mcp project structure` |
| **J1** | après-midi | models.py + tests #1, #2, #10 | `feat(models): pydantic schemas Question/SubQuestion/ResearchPlan` |
| **J2** | matin | LinearDecomposer + tests #3, #4 | `feat(decompose): linear strategy` |
| **J2** | après-midi | GraphDecomposer + tests #5, #6 | `feat(decompose): graph DAG strategy` |
| **J3** | matin | DispatchMatrix + YAML + tests #7, #14 | `feat(dispatch): yaml matrix loader` |
| **J3** | après-midi | SIGHUP + quality.py + tests #8, #9 | `feat(quality): 6-criteria scoring + sighup reload` |
| **J4** | matin | 4 templates Jinja2 + render.py + test #12 | `feat(prompts): domain templates jinja2` |
| **J4** | après-midi | server.py + tests #13, #15 | `feat(server): fastmcp stdio + 3 tools` |
| **J5** | matin | SKILL.md + 3 examples/ + tests réels | `feat(skill): SKILL.md + examples` |
| **J6** | matin | A/B report sur 5 cas | `test: A/B linear vs graph on 5 real cases` |
| **J6** | après-midi | Ajustements seuils si <4/5 | `tune: adjust thresholds based on AB report` |
| **J7** | (réserve) | Doc README + ADR DSPY_GATE | `docs: phase A README + dspy gate ADR` |

---

## Critère succès Phase A

Sur les 5 cas (clinique_burnout / juridique_fr_inaptitude / technique_mcp / multilingue_iso / mixte_télécons) :
- ≥4 cas atteignent `quality.overall > 0.7`
- A/B Linear vs Graph documenté dans `ab_report.md` (peu importe le winner — la mesure est l'objectif)

---

**Document source** : sortie routine `trig_01L2DLJzpDVJo5cAmGqTEeA1` (claude.ai/code, 2026-05-09T03:02:19Z UTC). Archivé tel quel comme référence Phase A.
