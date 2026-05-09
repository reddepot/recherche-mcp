# PROMPT AUDIT EXTERNE — recherche-mcp Phase A v0.2

> Modèle-agnostic. Copier ce prompt + URL repo dans n'importe quel modèle disposant d'accès web (ChatGPT DR, Gemini DR, Perplexity DR, Kimi, Qwen, Claude.ai, DeepSeek, Grok, etc.).

---

## Contexte

Tu es un auditeur externe indépendant invité à examiner un projet Python livré en Phase A par un développeur avancé (médecin du travail français + ingénieur logiciel). Le projet implémente un skill Claude Code et un serveur MCP Python pour la **décomposition orthogonale de questions de recherche complexes** en 4-6 sous-prompts experts spécialisés par domaine, avec annonce d'une **matrice de dispatch** vers des modèles d'IA candidats (Perplexity DR, OpenAI o3-DR, Anthropic web_search, Gemini DR Apps, ChatGPT DR, Kimi Swarm, Qwen Max DR, Codex/Gemini/Kimi CLI).

Phase A = formalisation de la méthode (heuristique pure, sans LLM call). Phase B (35-50 j-h) automatisera l'appel aux APIs DR.

**URL du repo public à auditer** : https://github.com/reddepot/recherche-mcp

## Ce qui a déjà été fait

- DEVCODE-Vote P0 sur 13 voix initiales + 4 voix challenge (consolidé dans ADR mémoire)
- POLYLENS allégé interne 4 voix occidentales (Claude + Codex GPT-5.5 + Gemini 3.1 Pro + Kimi K2.6) sur 3 axes : qualité de code, tests, architecture
- Phase A v0.1 livrée → POLYLENS findings → Phase A v0.2 avec 26 tests additionnels
- 68/68 tests verts (pytest)
- 5 commits propres, rapport POLYLENS interne dans `docs/polylens_audit_phaseA_20260509.md`

## Ce qui t'est demandé maintenant

Audit externe **indépendant et impitoyable**. Apporte une perspective extérieure que les voix internes pourraient avoir manquée. Tu n'es pas tenu de respecter les choix de design existants — challenge-les si tu vois mieux.

### 4 axes d'audit

#### Axe 1 — Sécurité & robustesse

- Anti-PII (`src/recherche_mcp/safety.py`) : patterns regex FR (NIR, dates, téléphones, emails) — couverture complète ? Faux positifs/négatifs critiques ?
- Concurrence : `DispatchMatrix` singleton avec RLock, `_MODEL` SentenceTransformer thread-safe — race conditions latentes ?
- Logging : Formatter PII redaction — fuites possibles via stdout MCP, traces tierces ?
- Gestion d'erreurs : exceptions silencieuses, validation YAML, validators Pydantic — chemins d'attaque par input malformé ?

#### Axe 2 — Architecture & design

- Façade `MCPServerPort` avec `FastMCPAdapter` : vrai découplage du SDK ?
- Singleton `DispatchMatrix` : justifié ou anti-pattern ? Alternatives DI ?
- Decomposers (Linear/Graph) : factory + ABC, extensibilité Phase B ?
- Couplage skill `~/.claude/skills/recherche/SKILL.md` ↔ MCP server : étanche ?
- `decompose.py:DSPY_GATE` : 3 conditions de réveil DSPy MIPROv2 inscrites en commentaire — judicieux ou vœu pieux ?

#### Axe 3 — Qualité de code Python idiomatique 2026

- Pydantic v2 : validators correctement utilisés (`@field_validator` vs `@model_validator` après) ?
- Python 3.13 : `StrEnum` vs `str, Enum`, type hints complets, `match` exhaustif ?
- Tests : pyramide unit/integ correcte, fixtures isolantes, marqueurs cohérents, faux positifs ?
- Conventions : snake_case, docstrings, ruff-compliance ?

#### Axe 4 — Méthodologie de décomposition orthogonale

C'est le cœur conceptuel : décomposer une question complexe en 4-6 sous-questions **MECE** (Mutually Exclusive Collectively Exhaustive) avec **angles complémentaires/contradictoires forcés**, dispatch vers **1-3 modèles spécialisés par sous-prompt**.

- 7 axes canoniques `_CANONICAL_AXES` dans `decompose.py` (definition / etat_art / cadre_normatif / praticien_cible / risques_limites / operationnalisation / comparaison_int) : pertinents ? complets ? biaisés vers SST/médecine du travail ?
- Stratégies Linear vs Graph : laquelle gagne sur quels types de questions ? L'A/B test des 5 cas réels (`tests/fixtures/cases.yaml`) est-il représentatif ?
- 6 critères de qualité (Couverture / Orthogonalité / Autonomie / Clarté / Balance / Traçabilité) dans `quality.py` : métriques bien choisies ? Heuristiques limites Phase A documentées ?
- Matrice dispatch (`data/dispatch_matrix.yaml`) : couverture domaines (clinique, juridique_fr, technique, multilingue, mixte) cohérente avec les forces réelles 2026 des modèles cités ?

## Format de sortie attendu

Pour chaque finding, structure :

```
[AXE-N] [P0|P1|P2|P3] Titre court (≤ 80 chars)

Fichier:ligne (citation passage exact ≤ 3 lignes).
Problème : 2-3 lignes max.
Mitigation proposée : 1-3 lignes max, code patch idéalement.
Référence externe : (optionnel) lien vers spec/RFC/paper si applicable.
```

Sévérités :
- **P0** = bloquant, à fixer avant tout merge ultérieur
- **P1** = à fixer avant Phase B
- **P2** = à fixer dans Phase B
- **P3** = nice-to-have, backlog long terme

## Règles dures

- **Cite TOUJOURS le fichier:ligne et le passage exact**
- Approbation sans citation = rejet (pas de consensus mou)
- Au moins **3 findings substantiels par axe** (4 axes × 3 = 12 minimum)
- Réponse en **français concis ≤ 2500 mots**, tags `[AXE-N]` `[Pn]`
- Termine par : (a) verdict synthétique 1 paragraphe, (b) liste prioritaire des **3 findings les plus critiques** à fixer en premier
- Cite des **sources externes** (spec MCP, RFC, papers académiques décomposition orthogonale 2025-2026, benchmarks DRBench/AutoResearchBench, etc.) quand pertinent — l'audit doit refléter l'état de l'art, pas seulement ton intuition

## Documentation interne déjà disponible (à consulter dans le repo)

- `README.md` — vue d'ensemble + commandes
- `docs/kickoff_phaseA_20260509.md` — kickoff Phase A complet (Opus 4.7)
- `docs/polylens_audit_phaseA_20260509.md` — audit interne 4 voix consolidé
- `docs/adr/0001-dspy-out-phase-a.md` — ADR DSPy MIPROv2 OUT avec 3 conditions de réveil
- `docs/ab_report_phase_a.md` — A/B Linear vs Graph 5/5 cas baseline
- `docs/phase_b_kickoff.md` — préparation Phase B avec backlog 12 items POLYLENS

Tu peux les ignorer pour rester indépendant, ou les utiliser pour comprendre les choix avant de les challenger.

## Output souhaité

1. Tableau récap findings par axe + sévérité
2. Détails par finding (format ci-dessus)
3. Verdict synthétique
4. **Top 3 findings P0/P1 prioritaires**
5. Sources externes citées (URLs)

Bon audit.
