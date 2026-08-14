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


def print_persistence(report: dict[str, Any]) -> None:
    run = report.get("run") or {}
    run_ids = report.get("run_ids") or []
    cohort = "fixed" if report.get("fixed_cohort") else "dynamic"
    print(
        f"PERSISTENCE | run=#{run.get('id')} query={run.get('query')!r} "
        f"runs={run_ids} cohort={cohort}"
    )
    print(
        f"common_seeds={report.get('common_seed_count', 0)} "
        f"seed_union={report.get('seed_union_count', 0)} "
        f"source_counts={report.get('source_counts', [])}"
    )
    if len(run_ids) < 2:
        print("Need at least 2 compatible runs before persistence is meaningful.")

    print("\nPERSISTENT RECOMMENDATION SIGNALS")
    for idx, item in enumerate(report.get("signals") or [], start=1):
        slope = item.get("support_slope_pp_per_run")
        slope_text = "n/a" if slope is None else f"{slope:+.2f}pp/run"
        median_rank = item.get("median_recommendation_rank")
        rank_text = "n/a" if median_rank is None else f"{median_rank:.1f}"
        print(
            f"{idx:>2}. present={item['runs_present']}/{item['runs_total']} "
            f"({item['presence_pct']:>5.1f}%) | "
            f"support_now={item['current_support_pct']:>5.1f}% | "
            f"support_med={item['median_support_when_present_pct']:>5.1f}% | "
            f"slope={slope_text:>12} | rank_med={rank_text:>4} | "
            f"score={item['persistence_score']:>5.1f} | {item['title'][:80]}"
        )


def print_contrast(report: dict[str, Any]) -> None:
    target = report.get("target_run") or {}
    print(
        f"NICHE CONTRAST | target_run=#{report.get('target_run_id')} "
        f"query={target.get('query')!r} controls={report.get('control_run_ids', [])}"
    )
    print(
        f"target_sources={report.get('target_source_count', 0)} "
        f"control_sources={report.get('control_source_counts', [])}"
    )

    print("\nNICHE-SPECIFIC RECOMMENDATION SIGNALS")
    for idx, item in enumerate(report.get("signals") or [], start=1):
        print(
            f"{idx:>2}. niche={item['niche_support_pct']:>5.1f}% | "
            f"control_avg={item['control_avg_support_pct']:>5.1f}% | "
            f"control_max={item['control_max_support_pct']:>5.1f}% | "
            f"specificity={item['specificity_vs_max_pp']:+6.1f}pp | "
            f"controls_hit={item['controls_present']}/{item['controls_total']} | "
            f"{item['title'][:80]}"
        )
