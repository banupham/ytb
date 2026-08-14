from __future__ import annotations

import argparse
import json
import os
import sys

from .analyzer import analyze
from .crawler import CrawlConfig, RecommendationCrawler
from .invidious import (
    INSTANCE_DIRECTORY_URL,
    InvidiousClient,
    InvidiousError,
    auto_select_client,
    discover_public_instances,
)
from .report import print_report, write_json
from .store import RadarStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytb-radar",
        description="Observe YouTube recommendation graphs through Invidious.",
    )
    parser.add_argument("--db", default="data/radar.db", help="SQLite database path")

    sub = parser.add_subparsers(dest="command", required=True)

    ping = sub.add_parser("ping", help="Check manual instance or auto-select a public one")
    _add_instance_args(ping)

    instances = sub.add_parser("instances", help="Show official public Invidious candidates")
    instances.add_argument("--timeout", type=float, default=8.0)
    instances.add_argument(
        "--directory-url",
        default=os.environ.get("YTB_INSTANCES_API", INSTANCE_DIRECTORY_URL),
        help="Official instance directory JSON URL",
    )

    scan = sub.add_parser("scan", help="Search seeds then crawl recommendedVideos")
    scan.add_argument("--query", required=True, help="Seed search query")
    _add_instance_args(scan)
    _add_crawl_args(scan)

    scan_ids = sub.add_parser("scan-ids", help="Crawl from explicit YouTube video IDs")
    scan_ids.add_argument("video_ids", nargs="+")
    scan_ids.add_argument("--label", default=None, help="Optional run label/query")
    _add_instance_args(scan_ids)
    _add_crawl_args(scan_ids)

    ana = sub.add_parser("analyze", help="Analyze a completed crawl")
    ana.add_argument("--run-id", type=int, default=None)
    ana.add_argument("--top", type=int, default=20)
    ana.add_argument("--json-out", default=None)

    export = sub.add_parser("export", help="Export analysis JSON")
    export.add_argument("--run-id", type=int, default=None)
    export.add_argument("--top", type=int, default=100)
    export.add_argument("--out", required=True)

    return parser


def _add_instance_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--instance",
        default=os.environ.get("YTB_INVIDIOUS_BASE"),
        help=(
            "Pin one Invidious base URL. If omitted, ytb-radar reads the official "
            "instance directory and probes candidates automatically."
        ),
    )
    parser.add_argument("--region", default=os.environ.get("YTB_REGION", "VN"))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--directory-url",
        default=os.environ.get("YTB_INSTANCES_API", INSTANCE_DIRECTORY_URL),
        help=argparse.SUPPRESS,
    )


def _add_crawl_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seed-limit", type=int, default=20)
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--recs", type=int, default=20, help="Recommendations per fetched video")
    parser.add_argument("--max-videos", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between fetches in seconds")


def _client(args: argparse.Namespace) -> InvidiousClient:
    if args.instance:
        print(f"Invidious: pinned {args.instance}", file=sys.stderr)
        return InvidiousClient(args.instance, region=args.region, timeout=args.timeout)

    print("Invidious: auto-selecting from official public instances...", file=sys.stderr)
    client, diagnostics = auto_select_client(
        region=args.region,
        timeout=args.timeout,
        directory_url=args.directory_url,
    )
    for line in diagnostics:
        print(f"  {line}", file=sys.stderr)
    print(f"Invidious: selected {client.base_url}", file=sys.stderr)
    return client


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = RadarStore(args.db)

    try:
        if args.command == "instances":
            rows = discover_public_instances(
                directory_url=args.directory_url,
                timeout=args.timeout,
            )
            if not rows:
                print("No healthy HTTPS candidates found.")
                return 2
            print("OFFICIAL PUBLIC INVIDIOUS CANDIDATES")
            for row in rows:
                api = "yes" if row.api_advertised is True else "no" if row.api_advertised is False else "?"
                uptime = f"{row.uptime:.3f}%" if row.uptime is not None else "?"
                print(
                    f"{row.uri:42} api={api:3} uptime={uptime:9} host_region={row.region or '?'}"
                )
            return 0

        if args.command == "ping":
            client = _client(args)
            stats = client.stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            return 0

        if args.command in {"scan", "scan-ids"}:
            client = _client(args)
            config = CrawlConfig(
                seed_limit=args.seed_limit,
                depth=max(0, args.depth),
                recs_per_video=max(1, args.recs),
                max_videos=max(1, args.max_videos),
                delay=max(0.0, args.delay),
            )
            crawler = RecommendationCrawler(client, store, config)
            if args.command == "scan":
                run_id = crawler.scan_query(args.query)
            else:
                run_id = crawler.scan_video_ids(args.video_ids, query=args.label)
            print(f"crawl complete: run_id={run_id}")
            report = analyze(store, run_id=run_id, top_n=10)
            print_report(report)
            return 0

        if args.command == "analyze":
            report = analyze(store, run_id=args.run_id, top_n=args.top)
            print_report(report)
            if args.json_out:
                write_json(report, args.json_out)
                print(f"\nJSON written: {args.json_out}")
            return 0

        if args.command == "export":
            report = analyze(store, run_id=args.run_id, top_n=args.top)
            write_json(report, args.out)
            print(args.out)
            return 0

    except InvidiousError as exc:
        print(f"Invidious error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
