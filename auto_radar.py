from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ytb_radar.analyzer import analyze
from ytb_radar.cohort import cohort_run_label, read_cohort
from ytb_radar.crawler import CrawlConfig, RecommendationCrawler
from ytb_radar.report import write_json
from ytb_radar.signals import contrast_report, persistence_report
from ytb_radar.store import RadarStore
from ytb_radar.youtube_browser import YouTubeBrowserProvider


DEFAULT_CONTROLS = [
    "nhạc bolero trữ tình",
    "bán nhà bình chánh",
]


def _slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip()).strip("_")
    return value[:60] or "control"


def _provider(args: argparse.Namespace) -> YouTubeBrowserProvider:
    return YouTubeBrowserProvider(
        region=args.region,
        timeout=args.timeout,
        headless=not args.headed,
        browser_channel=args.browser_channel,
        isolate_watch_context=True,
    )


def _config(args: argparse.Namespace, seed_limit: int) -> CrawlConfig:
    return CrawlConfig(
        seed_limit=seed_limit,
        depth=0,
        recs_per_video=max(1, args.recs),
        max_videos=max(seed_limit, args.max_videos),
        delay=max(0.0, args.delay),
    )


def _scan_cohort(
    store: RadarStore,
    args: argparse.Namespace,
    cohort: dict[str, Any],
) -> int:
    provider = _provider(args)
    try:
        crawler = RecommendationCrawler(
            provider,
            store,
            _config(args, len(cohort["video_ids"])),
        )
        label = cohort_run_label(cohort["label"], cohort["video_ids"])
        return crawler.scan_video_ids(cohort["video_ids"], query=label)
    finally:
        provider.close()


def _scan_control(
    store: RadarStore,
    args: argparse.Namespace,
    query: str,
) -> int:
    provider = _provider(args)
    try:
        crawler = RecommendationCrawler(
            provider,
            store,
            _config(args, args.seed_limit),
        )
        return crawler.scan_query(query)
    finally:
        provider.close()


def _summary_text(
    *,
    stamp: str,
    cohort: dict[str, Any],
    fixed_run_id: int,
    control_runs: list[tuple[str, int]],
    persistence: dict[str, Any],
    contrast: dict[str, Any],
    out_dir: Path,
) -> str:
    lines: list[str] = []
    lines.append("YTB RADAR AUTO REPORT")
    lines.append(f"time={stamp}")
    lines.append(
        f"cohort={cohort['label']} seeds={len(cohort['video_ids'])} signature={cohort['signature']}"
    )
    lines.append(f"fixed_run={fixed_run_id}")
    lines.append("control_runs=" + ", ".join(f"{query!r}:#{rid}" for query, rid in control_runs))
    lines.append("")

    lines.append("TOP PERSISTENT SIGNALS")
    for idx, row in enumerate((persistence.get("signals") or [])[:15], start=1):
        slope = row.get("support_slope_pp_per_run")
        slope_text = "n/a" if slope is None else f"{slope:+.2f}pp/run"
        lines.append(
            f"{idx:>2}. present={row['runs_present']}/{row['runs_total']} "
            f"support_now={row['current_support_pct']:.1f}% "
            f"support_med={row['median_support_when_present_pct']:.1f}% "
            f"slope={slope_text} | {row['title']}"
        )

    lines.append("")
    lines.append("TOP NICHE-SPECIFIC SIGNALS")
    for idx, row in enumerate((contrast.get("signals") or [])[:15], start=1):
        lines.append(
            f"{idx:>2}. niche={row['niche_support_pct']:.1f}% "
            f"control_max={row['control_max_support_pct']:.1f}% "
            f"specificity={row['specificity_vs_max_pp']:+.1f}pp "
            f"controls={row['controls_present']}/{row['controls_total']} | {row['title']}"
        )

    lines.append("")
    lines.append(f"details={out_dir}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one fixed-cohort scan, unrelated controls, persistence, contrast, and export files."
    )
    parser.add_argument("--db", default="data/radar.db")
    parser.add_argument("--cohort", default="cohorts/minecraft_sinh_ton.json")
    parser.add_argument(
        "--control",
        action="append",
        dest="controls",
        help="Unrelated control query. Repeat for multiple controls.",
    )
    parser.add_argument("--region", default="VN")
    parser.add_argument("--seed-limit", type=int, default=20)
    parser.add_argument("--recs", type=int, default=20)
    parser.add_argument("--max-videos", type=int, default=200)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--browser-channel", default="auto")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--out-root", default="reports/auto")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    controls = args.controls or DEFAULT_CONTROLS
    cohort_path = Path(args.cohort)
    if not cohort_path.exists():
        raise SystemExit(f"Missing cohort file: {cohort_path}")

    cohort = read_cohort(cohort_path)
    store = RadarStore(args.db)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_root) / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/{2 + len(controls)}] fixed cohort: {cohort['label']}")
    fixed_run_id = _scan_cohort(store, args, cohort)
    fixed_analysis = analyze(store, run_id=fixed_run_id, top_n=args.top)
    write_json(fixed_analysis, out_dir / "fixed_analysis.json")

    control_runs: list[tuple[str, int]] = []
    for index, query in enumerate(controls, start=2):
        print(f"[{index}/{2 + len(controls)}] control: {query}")
        run_id = _scan_control(store, args, query)
        control_runs.append((query, run_id))
        write_json(
            analyze(store, run_id=run_id, top_n=args.top),
            out_dir / f"control_{_slug(query)}_run_{run_id}.json",
        )

    print(f"[{2 + len(controls)}/{2 + len(controls)}] analyze + export")
    persistence = persistence_report(
        store,
        run_id=fixed_run_id,
        window=max(1, args.window),
        top_n=args.top,
    )
    contrast = contrast_report(
        store,
        target_run_id=fixed_run_id,
        control_run_ids=[run_id for _query, run_id in control_runs],
        top_n=args.top,
    )
    write_json(persistence, out_dir / "persistence.json")
    write_json(contrast, out_dir / "contrast.json")

    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cohort_file": str(cohort_path),
        "cohort_label": cohort["label"],
        "cohort_signature": cohort["signature"],
        "fixed_run_id": fixed_run_id,
        "control_runs": [
            {"query": query, "run_id": run_id} for query, run_id in control_runs
        ],
        "region": args.region,
        "recs": args.recs,
        "persistence_window": args.window,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = _summary_text(
        stamp=stamp,
        cohort=cohort,
        fixed_run_id=fixed_run_id,
        control_runs=control_runs,
        persistence=persistence,
        contrast=contrast,
        out_dir=out_dir,
    )
    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")
    latest = Path(args.out_root).parent / "latest_summary.txt"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(summary, encoding="utf-8")

    print("DONE")
    print(f"summary: {out_dir / 'summary.txt'}")
    print(f"latest : {latest}")
    print(f"details: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
