# recherche-mcp — MCP server pour décomposition orthogonale + dispatch matrice

**Phase A v0.1 — Voie 3 minimal** (8-12 j-h, 2026-05-09 → +1 sem)

Serveur MCP exposant 3 outils pour formaliser la décomposition orthogonale de questions de recherche complexes en 4-6 sous-prompts experts spécialisés par domaine, avec annonce de matrice dispatch vers modèles candidats (Perplexity DR, OpenAI o3, Anthropic web_search, Gemini DR, Kimi Swarm, Qwen Max DR, Codex/Gemini/Kimi CLI).

Conçu comme **back-end métier** du skill Claude Code `/recherche` (front-end conversationnel passif).

## Statut

🚧 Phase A en construction (Jour 1, 2026-05-09).

## Décisions structurelles

Issues du DEVCODE-Vote P0 sur 13 voix initiales + 4 voix challenge (ADR : `~/.claude/projects/-Users-radu/memory/decision_recherche_skill_devcode_20260508.md`) :

- **D Hybride packaging** : Python MCP server + skill `.md` léger + binding CLI optionnel
- **H' Décomposition orthogonale** 4-6 sous-questions MECE (graphe ou linéaire, A/B testable)
- **Transport stdio** uniquement (pas Streamable HTTP en LAN-only)
- **DSPy MIPROv2 OUT** Phase A (`DSPY_GATE` en commentaire `decompose.py`)

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

## Critère succès Phase A

Sur 5 cas réels (clinique / juridique_fr / technique / multilingue / mixte) :
- ≥4 cas atteignent `quality.overall > 0.7`
- A/B Linear vs Graph documenté dans `ab_report.md`

## Roadmap

- **Phase B (35-50 j-h)** : auto API DR (Perplexity Sonar, OpenAI o3-DR, Anthropic web_search, xAI grok), policy engine, mode express, logs hash-chain. Voir ADR.
- **Phase C (88-132 j-h)** : LangGraph orchestrateur + 4 sub-agents + Postgres checkpointer + NLI checker + dossier argumentaire JSON + revue CNIL/HDS. Voir ADR.

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

- `docs/kickoff_phaseA_20260509.md` — kickoff document complet (Opus 4.7)
- `docs/polylens_audit_phaseA_20260509.md` — audit POLYLENS allégé 4 voix
- `docs/phase_b_kickoff.md` — préparation Phase B (γ-α dispatch auto)
- `docs/decisions/` — ADRs locaux du projet
- `docs/ab_report_phase_a.md` — A/B Linear vs Graph 5/5 cas baseline

## Licence

Proprietary — usage personnel.
