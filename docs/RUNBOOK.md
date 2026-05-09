# recherche-mcp — Runbook

> 1 page. Start, debug, restore. If it doesn't fit here, it doesn't
> belong in a runbook.

## Quick start (cold clone)

```bash
git clone <repo>
cd recherche_mcp
uv sync --all-extras
uv run python -c 'import recherche_mcp'
```

If the smoke import fails, you have a build/install problem — see
"Common errors" below before going further.

## Run the tests

```bash
uv run pytest --no-cov -q
```

Expected: green. If red, do **not** push fixes; treat the failure as
a wake-event (see `docs/SUNSET_NOTICE.md`).

## Lint & types

```bash
uv run ruff check .
uv run mypy src/
```

## Common errors


### `ModuleNotFoundError`

`uv sync --all-extras` was probably
skipped. Re-run, then re-run the smoke command.

### `pytest` collection error

Ensure you are inside the activated venv (`uv run` handles this) and
that `pyproject.toml` is intact.


## Restore from freeze

If the project must be reactivated:

```bash
git checkout maintenance
git tag -l "freeze-*" | tail -1
sunset-it audit . --profile solo-frozen
sunset-it reactivate . --reason "<short justification>"
```

The `reactivate` step creates a new branch off `maintenance` and
drops the freeze banner from the README.

## Watch policy

The CI workflow `.github/workflows/sunset.yml` runs
`sunset-it watch` weekly. Any wake event (CVE, dep EOL, model
deprecation) opens a labelled GitHub issue. Address it, run
`sunset-it audit`, decide: ignore (close the issue with reason),
patch on `maintenance`, or full reactivate.

---

*Scaffolded by `sunset-it knowledge` on
2026-05-09. Keep it short. If it grows
beyond a page, split into per-incident docs under `docs/runbooks/`.*
