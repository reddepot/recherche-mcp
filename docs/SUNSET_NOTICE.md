# Sunset / Freeze Notice — recherche-mcp

> One-page status. If a future maintainer (or future-you) lands on
> the repo, this tells them what they're looking at.

## Status

**FROZEN** as of
2026-05-09.

## What this means

- No active development. Bug fixes and security patches accepted on the maintenance branch only.

## Why

TODO: short rationale (1-2 sentences). E.g.,
the project reached its functional goal and the maintainer is moving
to other work. The state is stable; the freeze is reversible if a
real need arises.

## Reactivation policy

- **Trigger conditions**: CVE Critical/High on direct dependency, Python runtime EOL, model used has retirement < 90 days, real user need.
- **How**: see `docs/RUNBOOK.md` "Restore from freeze" + run
  `sunset-it reactivate .` to formalise the exit.

## Maintenance window

- Branch: `maintenance`
- Last known-good tag: `TODO`
- Watch policy: see `.github/workflows/sunset.yml` (runs
  `sunset-it watch` weekly).

## Contact


No active maintainer. File an issue or fork at your discretion.


---

*Scaffolded by `sunset-it knowledge` on
2026-05-09.*
