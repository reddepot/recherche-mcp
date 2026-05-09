# recherche-mcp — MCP server pour décomposition orthogonale + dispatch matrice

Serveur MCP exposant 3 outils pour formaliser la **décomposition orthogonale** de questions de recherche complexes en 4-6 sous-prompts experts spécialisés par domaine, avec annonce de **matrice de dispatch** vers modèles candidats (Perplexity DR, OpenAI o3-DR, Anthropic web_search, Gemini DR, Kimi Swarm, Qwen Max DR, Codex/Gemini/Kimi CLI).

Conçu comme **back-end métier** du skill Claude Code `/recherche` (front-end conversationnel passif).

## Statut

Phase A livrée et auditée. Phase B (auto API DR) en préparation — voir `docs/phase_b_kickoff.md`.

## Décisions structurelles

- **Hybride packaging** : Python MCP server (FastMCP) + skill `.md` léger + binding CLI optionnel
- **Décomposition orthogonale** 4-6 sous-questions MECE (graphe ou linéaire, A/B testable)
- **Axes par domaine** chargés depuis `data/axes_by_domain.yaml` (clinique, juridique_fr, technique, multilingue, mixte)
- **Pondération qualité par domaine** (`data/quality_weights.yaml`, ADR-0002)
- **Transport stdio** uniquement en Phase A (Streamable HTTP + OAuth réservés Phase B/C)
- **DSPy MIPROv2 OUT** Phase A (`DSPY_GATE` 3 conditions de réveil dans `decompose.py`)

## Architecture

```
Skill SKILL.md (passif)
   ↓ stdio
recherche-mcp (FastMCP)
   ├── decompose_question  ── Linear / Graph (factory)
   ├── generate_subprompts ── Jinja2 templates par domaine
   └── catalog_sources     ── DispatchMatrix YAML + SIGHUP
```

## Installation

```bash
cd ~/Developer/projects/recherche-mcp
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
recherche-mcp --help
```

## Tests

```bash
pytest                              # tous tests
pytest -m unit                      # rapides uniquement
pytest tests/test_ab_strategies.py  # A/B Linear vs Graph
```

## Usage (Phase A — annonce dispatch, pas d'auto API)

```python
# Via le skill /recherche dans Claude Code
# ou en direct :
from recherche_mcp.decompose import make_decomposer
from recherche_mcp.models import Question, Strategy, Domain

q = Question(text="...", domain=Domain.CLINIQUE)
plan = make_decomposer(Strategy.LINEAR).decompose(q)
print(plan.model_dump_json(indent=2))
```

## Critère succès Phase A (heuristique pure, sans LLM)

**Baseline empirique mesurée** (cf `docs/ab_report_phase_a.md`) :
- ≥4 cas sur 5 atteignent `quality.overall > 0.5`
- `quality.orthogonalite > 0.05` (cosine max ≤ 0.95)
- A/B Linear vs Graph documenté

**Cible Phase B avec LLM-driven decomposition** :
- `quality.overall > 0.7`
- `quality.orthogonalite > 0.4`
- Mode "express" < 5s pour P2

Les seuils 0.7 / 0.4 ne sont pas atteignables par la heuristique pure Phase A —
ils nécessitent l'auto API DR (Phase B).

## Roadmap

- **Phase B (estim. 25-40 j-h)** : auto API DR (Perplexity Sonar, OpenAI o3-DR, Anthropic web_search, xAI grok), policy engine côté serveur, mode express bypass, audit hash-chain, fallback Mistral local. Voir `docs/phase_b_kickoff.md`.
- **Phase C (estim. 60-100 j-h)** : LangGraph orchestrateur + sub-agents spécialisés + Postgres checkpointer + NLI checker + dossier argumentaire JSON + revue CNIL/HDS pour usage opposable médico-légal.

## Logs usage permanent (Phase A → B data-driven)

Chaque invocation de `decompose_question` écrit un événement JSONL dans
`runs/usage_YYYY-MM.jsonl` (rotation mensuelle, anti-PII appliqué).

Synthèse pour itération Phase B :
```bash
python scripts/usage_summary.py            # tous mois
python scripts/usage_summary.py 2026-05    # mois spécifique
python scripts/usage_summary.py --json     # JSON brut
```

Mode privacy strict : `recherche-mcp --no-log` (désactive logging + usage JSONL).

Override path : `RECHERCHE_MCP_RUNS_DIR=/custom/path` env var.

## Doc

- `docs/decisions/` — ADRs actifs du projet
  - `0001-dspy-out-phase-a.md` — DSPY_GATE (3 conditions de réveil DSPy MIPROv2)
  - `0002-quality-weights.md` — pondération des 6 critères qualité par domaine
- `docs/ab_report_phase_a.md` — A/B Linear vs Graph 5/5 cas baseline
- `docs/phase_b_kickoff.md` — préparation Phase B (γ-α dispatch auto)
- `docs/audit_external_prompt.md` — prompt audit externe modèle-agnostic
- `docs/audit_gemini_prompt.md` — prompt audit externe spécifique Gemini DR Apps
- `docs/_archive/` — artefacts historiques (kickoff initial, audit POLYLENS interne)

## Licence

Proprietary — usage personnel.
