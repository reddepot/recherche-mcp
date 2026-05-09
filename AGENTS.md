# Agent Instructions for recherche-mcp

> Cross-tool agent context (Claude Code, Cursor, GitHub Copilot,
> Gemini CLI, Codex). Read this before generating code in this repo.

## Project overview

MCP server for orthogonal question decomposition + dispatch matrix (Phase A — Voie 3 minimal)

## Project status

- **State**: frozen
- **Frozen at**: 2026-05-09
- **Reactivation policy**: on-demand by maintainer; see RUNBOOK.md

## Build, test, lint

- **Install**: `uv sync --all-extras`
- **Tests**: `uv run pytest`
- **Lint**: `uv run ruff check .`
- **Type check**: `uv run mypy src/`
- **Smoke**: `uv run python -c 'import recherche_mcp'`

## Conventions to respect


- Python ≥ >=3.13
- mypy `--strict` clean
- ruff clean (config in `pyproject.toml`)
- No new runtime dependency without an ADR


## Known pitfalls


- (none documented yet — add as you discover them)


## Areas not to evolve without re-evaluation


- See `docs/adr/` for architectural decisions that should not change
  without writing a superseding ADR.


## Security boundary

- No secrets in source. Use `.env.example` as the template; real
  secrets stay in `.env` (gitignored) or in the secret manager.
- Do not generate `pull_request_target` workflows.
- Do not commit lockfiles modifications without re-running the
  full test suite first.

## Reactivation contract

If you (a future agent or human) need to extend this project:

1. Read `docs/RUNBOOK.md` to bring the environment back up.
2. Read `AI_GENERATION_MANIFEST.md` to know which models produced
   what, and which prompts are load-bearing.
3. Run `sunset-it audit . --profile solo-frozen`
   to confirm the freeze invariants still hold before any change.
4. After your change, re-run `sunset-it audit .` and either keep the
   audit green or document the new state in `LESSONS.md`.

---

*This file was scaffolded by `sunset-it knowledge` on
2026-05-09. Edit it freely — it is
yours, not the tool's.*
