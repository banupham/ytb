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
    if report.get("previous_run_id"):
        print(f"compared_with_run={report['previous_run_id']}")

    print("\nTOP RECOMMENDATION LEADERS")
    for idx, item in enumerate(report["recommendation_leaders"], start=1):
        growth = (
            "new"
            if item["previous_recommended_by"] == 0
            else f"{item['growth_pct']:+.1f}%"
        )
        print(
            f"{idx:>2}. {item['recommended_by']:>3} refs | "
            f"rank={item['rank_score']:.2f} | bridge={item['bridge_score']:.2f} | "
            f"growth={growth:>8} | {item['title'][:80]}"
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
