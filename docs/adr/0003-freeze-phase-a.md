# ADR-0003 — Freeze Phase A en attendant les conditions Phase B

**Date** : 2026-05-09
**Statut** : Accepté
**Référence** : ADR principal du projet (mémoire utilisateur), `docs/phase_b_kickoff.md`.

## Contexte

Phase A v0.3 est livrée et stable :
- 106 tests verts, 14 commits propres sur `main`
- Audits internes (POLYLENS 4 voix) et externes (4 modèles V1) traités
- 18 findings fixés, backlog Phase B réduit à 5 items résiduels
- Repo public : https://github.com/reddepot/recherche-mcp

Le passage à Phase B (γ-α dispatch auto, 25-40 j-h estimés) requiert
des données empiriques pour calibrer la pondération des critères
qualité (ADR-0002) et arbitrer Linear vs Graph par domaine. Ces
données proviendront du log usage `runs/usage_*.jsonl` après ≥30
invocations réelles du skill `/recherche` (cf DSPY_GATE condition
(a) dans `decompose.py`).

À 1-2 invocations/jour estimées, le seuil 30 sera atteint en ~3
semaines. Pendant cette période, le projet n'a **rien à coder** —
seul l'instrumentation collecte les données.

## Décision

**Freeze Phase A** dès maintenant via `sunset-it lockdown` :
- Tag annoté `freeze-phase-a-20260509`
- Branche maintenance `maintenance/phase-a`
- Bannière README "frozen, reversible"

Réactivation prévue via `sunset-it reactivate` quand :
- Notification automatique GO Phase B atteinte (cf
  `docs/threshold_alert_setup.md`, seuil 30 invocations)
- Décision explicite « GO Phase B » par le mainteneur

## Justification

### Pourquoi freezer maintenant plutôt que continuer ?

- Aucun travail technique restant Phase A (backlog absorbé par les
  audits externes).
- Risque de modifications de complaisance si le projet reste « actif »
  (refactors cosmétiques, ajouts hors scope).
- L'instrumentation usage tourne en autonomie — pas besoin de présence
  dev.
- Le tag freeze est un point de référence mesurable pour Phase B
  (delta clair entre baseline figée et améliorations Phase B).

### Pourquoi pas un sunset / archive définitif ?

- Phase B est planifiée et viable (25-40 j-h estimés, backlog
  documenté).
- Le seuil 30 invocations est réaliste sur 3 semaines d'usage MdT FR.
- `sunset-it` permet `reactivate` propre avec strip banner + commit +
  tag d'unfreeze, sans perte d'historique.

### Pourquoi le tag `freeze-phase-a-20260509` plutôt que `v0.3` ?

- `v0.3` suggère une release publiable (PyPI, etc.), ce que le projet
  n'est pas (LICENSE proprietary, usage personnel).
- `freeze-phase-a-` est explicite sur l'intention : freeze réversible
  d'une phase, pas release stable d'un produit.

## Conséquences

### Positives

- État du projet **lisible sans contexte** : la bannière README et le
  tag annoté disent immédiatement « phase A figée, voir Phase B
  conditions ».
- Reproductibilité : `uv.lock` committé avec versions résolues +
  manifeste IA (`AI_GENERATION_MANIFEST.md`) + runbook
  (`docs/RUNBOOK.md`).
- Permet à un futur agent (ou future-self) de reprendre proprement
  6-12 mois plus tard sans archéologie.

### Négatives / Risques

- Lock du tag/branche par convention seulement (Git ne bloque pas les
  pushs sur main).
- L'instrumentation usage continue d'écrire dans `runs/` (path XDG)
  même branche frozen — comportement voulu, mais à signaler dans le
  RUNBOOK.

### Réversibilité

`sunset-it reactivate .` strip la bannière, commit, tag d'unfreeze.
Aucune perte d'historique.

## Conditions de réactivation (rappelées)

Voir `docs/phase_b_kickoff.md` section "Conditions de GO" pour la
liste complète. En résumé :

1. ≥30 invocations réelles du skill `/recherche` enregistrées dans
   `runs/usage_*.jsonl`
2. Synthèse `python scripts/usage_summary.py` montrant signal
   exploitable (volumétrie suffisante par domaine, qualité baseline
   confirmée ou patterns d'échec identifiables)
3. Pas de bug P0/P1 émergent durant la période frozen
4. Décision explicite « GO Phase B »

Notification automatique de l'atteinte du seuil : email envoyé via
launchd macOS (cf `docs/threshold_alert_setup.md`).

## Évidence

- `sunset-it audit .` : YELLOW (0 blockers, 3 warnings adressés par
  cet ADR + `lockdown`).
- Dépendances figées : `uv.lock` committé, hashes inclus.
- Tests : 106/106 verts.
- Documentation freeze : `AGENTS.md`, `docs/RUNBOOK.md`,
  `AI_GENERATION_MANIFEST.md`, `docs/SUNSET_NOTICE.md`,
  `docs/LESSONS.md` générés par `sunset-it knowledge`.
