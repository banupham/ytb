from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .analyzer import analyze
from .crawler import CrawlConfig, RecommendationCrawler
from .invidious import (
    INSTANCE_DIRECTORY_URL,
    InvidiousClient,
    auto_select_client,
    discover_public_instances,
)
from .provider import ProviderError, RecommendationProvider
from .report import print_report, write_json
from .store import RadarStore
from .youtube_browser import YouTubeBrowserProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytb-radar",
        description="Observe YouTube recommendation graphs through a real browser or Invidious.",
    )
    parser.add_argument("--db", default="data/radar.db", help="SQLite database path")

    sub = parser.add_subparsers(dest="command", required=True)

    ping = sub.add_parser("ping", help="Check the configured recommendation provider")
    _add_provider_args(ping)

    instances = sub.add_parser("instances", help="Show official public Invidious candidates")
    instances.add_argument("--timeout", type=float, default=8.0)
    instances.add_argument(
        "--directory-url",
        default=os.environ.get("YTB_INSTANCES_API", INSTANCE_DIRECTORY_URL),
        help="Official instance directory JSON URL",
    )

    scan = sub.add_parser("scan", help="Search seeds then crawl recommendations")
    scan.add_argument("--query", required=True, help="Seed search query")
    _add_provider_args(scan)
    _add_crawl_args(scan)

    scan_ids = sub.add_parser("scan-ids", help="Crawl from explicit YouTube video IDs")
    scan_ids.add_argument("video_ids", nargs="+")
    scan_ids.add_argument("--label", default=None, help="Optional run label/query")
    _add_provider_args(scan_ids)
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


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["youtube", "invidious"],
        default=os.environ.get("YTB_PROVIDER", "youtube"),
        help="Recommendation source. Default: youtube (real browser).",
    )
    parser.add_argument("--region", default=os.environ.get("YTB_REGION", "VN"))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--browser-channel",
        default=os.environ.get("YTB_BROWSER_CHANNEL", "auto"),
        help="youtube provider: auto, chrome, msedge, or chromium",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=os.environ.get("YTB_HEADED", "").lower() in {"1", "true", "yes"},
        help="youtube provider: show the browser window instead of headless mode",
    )
    parser.add_argument(
        "--instance",
        default=os.environ.get("YTB_INVIDIOUS_BASE"),
        help="invidious provider: pin one base URL; otherwise auto-probe public instances",
    )
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
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between fetched watch pages")


def _provider(args: argparse.Namespace) -> RecommendationProvider:
    if args.provider == "youtube":
        provider = YouTubeBrowserProvider(
            region=args.region,
            timeout=args.timeout,
            headless=not args.headed,
            browser_channel=args.browser_channel,
        )
        mode = "headed" if args.headed else "headless"
        print(
            f"Provider: YouTube browser ({mode}, channel={args.browser_channel}, region={args.region})",
            file=sys.stderr,
        )
        return provider

    if args.instance:
        print(f"Provider: Invidious pinned {args.instance}", file=sys.stderr)
        return InvidiousClient(args.instance, region=args.region, timeout=args.timeout)

    print("Provider: Invidious auto-selecting from official public instances...", file=sys.stderr)
    client, diagnostics = auto_select_client(
        region=args.region,
        timeout=args.timeout,
        directory_url=args.directory_url,
    )
    for line in diagnostics:
        print(f"  {line}", file=sys.stderr)
    print(f"Provider: Invidious selected {client.base_url}", file=sys.stderr)
    return client


def _close_provider(provider: Any) -> None:
    close = getattr(provider, "close", None)
    if callable(close):
        close()


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
            provider = _provider(args)
            try:
                stats = getattr(provider, "stats")()
                print(json.dumps(stats, ensure_ascii=False, indent=2))
            finally:
                _close_provider(provider)
            return 0

        if args.command in {"scan", "scan-ids"}:
            provider = _provider(args)
            try:
                config = CrawlConfig(
                    seed_limit=args.seed_limit,
                    depth=max(0, args.depth),
                    recs_per_video=max(1, args.recs),
                    max_videos=max(1, args.max_videos),
                    delay=max(0.0, args.delay),
                )
                crawler = RecommendationCrawler(provider, store, config)
                if args.command == "scan":
                    run_id = crawler.scan_query(args.query)
                else:
                    run_id = crawler.scan_video_ids(args.video_ids, query=args.label)
            finally:
                _close_provider(provider)
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

    except ProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
