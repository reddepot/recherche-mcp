# AI Generation Manifest — recherche-mcp

> Document les LLMs utilisés pendant la vie du projet, les prompts
> qui ont compté, et les décisions à ne pas regénérer sans revue.
> Requis pour tout projet co-codé IA entrant en freeze.

## Project state

- **Freeze date** : 2026-05-09
- **Freeze tag** : (créé par `sunset-it lockdown`)
- **Primary language/runtime** : Python 3.13
- **Critical external APIs** : aucune en Phase A (Phase B introduira Perplexity DR, OpenAI o3-DR, Anthropic web_search, xAI grok)

## Models used during development

| Tool | Model | Période | Rôle principal | Notes |
|------|-------|---------|----------------|-------|
| Claude Code (local) | claude-opus-4-7 (1M context) | 2026-05-08 → 2026-05-09 | Architecture, implémentation, refactor, audits internes | Orchestrateur principal |
| Claude Code (remote routine) | claude-opus-4-7 | 2026-05-09 03:02 UTC | Kickoff Phase A (`docs/_archive/kickoff_phaseA_20260509.md`) | One-shot via `/schedule` |
| Codex CLI | gpt-5.5 (reasoning_effort=high) | 2026-05-08 → 2026-05-09 | Voix challenge POLYLENS interne, validation factuelle | Combo Kimi+Codex obligatoire pour recherches |
| Gemini CLI | gemini-3.1-pro-preview | 2026-05-08 → 2026-05-09 | Voix challenge POLYLENS interne, état de l'art MCP/AI Act | — |
| Kimi CLI | kimi-k2.6 (Moonshot) | 2026-05-08 → 2026-05-09 | Voix challenge POLYLENS interne (perspective non-occidentale) | — |
| OpenRouter direct | z-ai/glm-4.6, qwen/qwen3-max, deepseek/deepseek-r1 | 2026-05-08 | Voix challenge supplémentaires (DEVCODE-Vote 13 voix) | Bypass MCP NAS |
| ChatGPT/Perplexity DR | (modèles externes) | 2026-05-09 | Audit externe V1 (4 voix : ChatGPT/DeepSeek/Kimi/Grok) | 18 findings → fixés |

## Non-regenerable decisions

> Décisions qui dépendent du comportement d'un modèle spécifique à un
> moment donné. Re-jouer le prompt sur un modèle plus récent ne
> reproduira pas le même code. Si vous en changez une, écrire un nouvel
> ADR expliquant pourquoi.

- **DSPy MIPROv2 OUT Phase A** (cf `docs/adr/0001-dspy-out-phase-a.md`) :
  3 conditions cumulatives de réveil inscrites en commentaire
  `decompose.py`. La décision repose sur la maturité des frameworks
  d'optimisation au moment de l'analyse — réévaluer avant d'introduire
  une optimisation automatique.
- **Pondération des 6 critères qualité par domaine** (cf
  `docs/adr/0002-quality-weights.md`) : poids reflètent
  l'intuition initiale du designer 2026, à valider après ≥30
  décompositions notées.

## Load-bearing prompts

> Prompts qui ont produit des artefacts critiques.

- `docs/_archive/kickoff_phaseA_20260509.md` — kickoff Phase A produit
  par Opus 4.7 via routine `/schedule` (~3000 mots, scaffolding code +
  fixtures). C'est le document d'origine du projet.
- `docs/audit_external_prompt.md` — prompt audit externe modèle-agnostic
  (V2 post-fixes). Permet à n'importe quel modèle DR (ChatGPT,
  Perplexity, DeepSeek, Kimi, Grok, Claude) de produire un audit
  comparable.
- `docs/audit_gemini_prompt.md` — variante spécifique Gemini DR Apps
  (axes Vertex AI, multimodalité, Google Search Grounding).
- `docs/_archive/audit_external_prompt_v1.md` — prompt V1 (déjà passé
  par 4 modèles, 18 findings tous fixés).

## Known AI debt

| Domaine | Risque | Détection | Mitigation |
|---------|--------|-----------|------------|
| Test theatre | Tests écrits par le même modèle que le code peuvent valider le bug | Cross-model review POLYLENS interne (4 voix) + audits externes (4+ voix) | Property-based tests sur invariants Pydantic + tests A/B sur 5 cas réels |
| Model anchoring | Heuristique de décomposition pourrait dépendre d'un idiome modèle | Audit externe documente les 5 cas de test attendus | Refactor avant retraite du modèle utilisé pour générer les axes_by_domain.yaml |
| Prompt rot | Prompts d'audit V1/V2 pourraient sous-performer sur futurs modèles | Re-jouer périodiquement les prompts sur 1 modèle nouveau | Versioner les prompts + maintenir prompt V2 en clé canonique |
| Hallucinated imports | LLM aurait pu importer un package inexistant | `uv lock` (hashes) + import smoke `recherche-mcp --help` | Lockfile committé `uv.lock` avec versions résolues |

## Reactivation note

Si un modèle listé ci-dessus est retiré avant la réactivation Phase B,
documenter la substitution choisie dans `docs/LESSONS.md` et superseder
les ADRs concernés. Ne pas re-jouer silencieusement les prompts
d'origine sur un nouveau modèle — la sortie divergera subtilement et
vous passerez le mois suivant à debugger des fantômes.

Pour Phase B (γ-α dispatch auto), les modèles à intégrer dans la
matrice `dispatch_matrix.yaml` doivent être vérifiés à jour au moment
de l'implémentation (chaque fournisseur publie un calendrier
deprecation : OpenAI ≥60j, Anthropic ≥60j, Google variable).

---

*Scaffolded par `sunset-it knowledge` 2026-05-09, complété manuellement.*
