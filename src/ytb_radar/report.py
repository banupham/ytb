from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_report(report: dict[str, Any]) -> None:
    run = report.get("run") or {}
    summary = report["summary"]
    print(f"RUN #{run.get('id')} | query={run.get('query')!r} | status={run.get('status')}")
    print(
        f"videos={summary['videos']} edges={summary['edges']} "
        f"sources={summary['sources_crawled']} communities={summary['communities']}"
    )
    print(
        f"seeds_found={summary.get('seeds_found', 0)} "
        f"seed_fill={summary.get('seed_fill_pct', 0):.1f}% "
        f"seed_sources_success={summary.get('seed_sources_success', 0)} "
        f"seed_sources_failed={summary.get('seed_sources_failed', 0)}"
    )
    if report.get("previous_run_id"):
        print(
            f"compared_with_compatible_run={report['previous_run_id']} "
            f"seed_overlap={summary.get('seed_overlap', 0)} "
            f"seed_jaccard={summary.get('seed_jaccard_pct', 0):.1f}% "
            f"comparable_seed_sources={summary.get('comparable_seed_sources', 0)}"
        )
    else:
        print("growth_comparison=n/a (no earlier compatible run)")

    print("\nTOP RECOMMENDATION LEADERS")
    for idx, item in enumerate(report["recommendation_leaders"], start=1):
        status = item.get("comparison_status")
        if status == "new":
            growth = "new"
        elif status == "changed" and item.get("growth_pct") is not None:
            growth = f"{item['growth_pct']:+.1f}%"
        elif status == "outside-common":
            growth = "seed-shift"
        else:
            growth = "n/a"
        print(
            f"{idx:>2}. {item['recommended_by']:>3} refs | "
            f"support={item.get('support_rate_pct', 0):>5.1f}% | "
            f"rank={item['rank_score']:.2f} | bridge={item['bridge_score']:.2f} | "
            f"growth={growth:>10} | {item['title'][:80]}"
        )

    print("\nCOMMUNITIES")
    for item in report["communities"][:10]:
        print(f"#{item['id']} size={item['size']}: {item['label']}")

    print_expansion(report)


def print_expansion(report: dict[str, Any]) -> None:
    opportunities = report.get("expansion_opportunities") or []
    if not opportunities:
        return
    print("\nAUDIENCE/CLUSTER EXPANSION CANDIDATES")
    for idx, item in enumerate(opportunities[:10], start=1):
        print(
            f"{idx:>2}. #{item['from_community']} {item['from_label']} "
            f"-> #{item['to_community']} {item['to_label']} | "
            f"cross_edges={item['cross_edges']} "
            f"sources={item['unique_source_videos']} targets={item['unique_target_videos']}"
        )
