#!/usr/bin/env python3
"""Synthèse du log usage /recherche pour itération Phase A → B.

Usage:
    python scripts/usage_summary.py             # tous mois
    python scripts/usage_summary.py 2026-05     # mois spécifique
    python scripts/usage_summary.py --json      # output JSON brut

Lit les fichiers `runs/usage_YYYY-MM.jsonl` et produit :
- Volumétrie : N invocations, période couverte
- Distribution domain / strategy / n_subq
- Stats qualité : moyenne, médiane, p25, p75 par domaine
- Top 10 questions (excerpts) par fréquence implicite
- Anomalies : erreurs, latences > 1s, qualité < 0.4
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

# uv run script — ajout du src au path si besoin
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from recherche_mcp import usage  # noqa: E402


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def synthesize(month: str | None = None) -> dict:
    events = usage.read_events(month=month)
    if not events:
        return {"total_events": 0}

    qualities = [e.quality_overall for e in events]
    latencies = [e.latency_ms for e in events]

    by_domain: dict[str, list] = {}
    for e in events:
        d = e.domain or "auto"
        by_domain.setdefault(d, []).append(e)

    quality_by_domain = {
        d: {
            "n": len(evs),
            "mean_overall": round(statistics.mean(e.quality_overall for e in evs), 3),
            "median_overall": round(statistics.median(e.quality_overall for e in evs), 3),
            "mean_orthogonalite": round(
                statistics.mean(e.quality_orthogonalite for e in evs), 3
            ),
        }
        for d, evs in by_domain.items()
    }

    errors = [e for e in events if e.error]
    slow = [e for e in events if e.latency_ms > 1000]
    poor_quality = [e for e in events if e.quality_overall < 0.4]

    return {
        "total_events": len(events),
        "first_event": events[0].timestamp,
        "last_event": events[-1].timestamp,
        "domain_distribution": dict(Counter(e.domain or "auto" for e in events)),
        "strategy_distribution": dict(Counter(e.strategy for e in events)),
        "n_subq_distribution": dict(Counter(e.n_subq_requested for e in events)),
        "quality_global": {
            "mean_overall": round(statistics.mean(qualities), 3),
            "median_overall": round(statistics.median(qualities), 3),
            "p25_overall": round(_percentile(qualities, 0.25), 3),
            "p75_overall": round(_percentile(qualities, 0.75), 3),
            "min_overall": round(min(qualities), 3),
            "max_overall": round(max(qualities), 3),
        },
        "quality_by_domain": quality_by_domain,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p95": round(_percentile(latencies, 0.95), 1),
            "max": round(max(latencies), 1),
        },
        "anomalies": {
            "n_errors": len(errors),
            "n_slow_above_1s": len(slow),
            "n_poor_quality_below_0.4": len(poor_quality),
            "error_samples": [
                {"ts": e.timestamp, "error": e.error, "excerpt": e.question_excerpt}
                for e in errors[:5]
            ],
        },
        "recent_questions": [
            {
                "ts": e.timestamp,
                "domain": e.domain or "auto",
                "strategy": e.strategy,
                "overall": round(e.quality_overall, 3),
                "excerpt": e.question_excerpt,
            }
            for e in events[-10:]
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("month", nargs="?", default=None, help="ex: 2026-05")
    parser.add_argument("--json", action="store_true", help="Output JSON brut")
    args = parser.parse_args()

    summary = synthesize(args.month)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    if summary["total_events"] == 0:
        print("Aucun event d'usage enregistré.")
        return

    print(f"=== Synthèse usage /recherche ({args.month or 'tous mois'}) ===\n")
    print(f"Total events : {summary['total_events']}")
    print(f"Période : {summary['first_event']} → {summary['last_event']}\n")

    print("## Distribution domaine")
    for d, n in summary["domain_distribution"].items():
        print(f"  {d:20s} : {n}")
    print()

    print("## Distribution stratégie")
    for s, n in summary["strategy_distribution"].items():
        print(f"  {s:20s} : {n}")
    print()

    print("## Distribution n_subq")
    for n_subq, n in sorted(summary["n_subq_distribution"].items()):
        print(f"  {n_subq:2d} : {n}")
    print()

    print("## Qualité globale")
    qg = summary["quality_global"]
    print(
        f"  overall : mean={qg['mean_overall']} median={qg['median_overall']} "
        f"p25={qg['p25_overall']} p75={qg['p75_overall']} "
        f"min={qg['min_overall']} max={qg['max_overall']}"
    )
    print()

    print("## Qualité par domaine")
    for d, q in summary["quality_by_domain"].items():
        print(
            f"  {d:20s} (n={q['n']:3d}) : "
            f"mean_overall={q['mean_overall']} "
            f"median={q['median_overall']} "
            f"mean_ortho={q['mean_orthogonalite']}"
        )
    print()

    print("## Latence (ms)")
    lat = summary["latency_ms"]
    print(
        f"  mean={lat['mean']} median={lat['median']} p95={lat['p95']} max={lat['max']}"
    )
    print()

    print("## Anomalies")
    a = summary["anomalies"]
    print(f"  Erreurs : {a['n_errors']}")
    print(f"  Latence > 1s : {a['n_slow_above_1s']}")
    print(f"  Qualité < 0.4 : {a['n_poor_quality_below_0.4']}")
    if a["error_samples"]:
        print("\n  Échantillons d'erreurs :")
        for e in a["error_samples"]:
            print(f"    [{e['ts']}] {e['error']}: {e['excerpt'][:80]}")
    print()

    print("## 10 dernières questions")
    for q in summary["recent_questions"]:
        print(
            f"  [{q['ts'][:19]}] {q['domain']:12s} {q['strategy']:6s} "
            f"overall={q['overall']:.2f} : {q['excerpt'][:80]}"
        )


if __name__ == "__main__":
    main()
