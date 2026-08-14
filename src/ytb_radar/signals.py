from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any

from .store import RadarStore


def _support_by_target(edges: list[dict[str, Any]]) -> tuple[set[str], dict[str, float]]:
    sources = {str(edge["source_id"]) for edge in edges}
    recommenders: defaultdict[str, set[str]] = defaultdict(set)
    for edge in edges:
        recommenders[str(edge["target_id"])].add(str(edge["source_id"]))
    if not sources:
        return sources, {}
    support = {
        target: (len(source_ids) / len(sources)) * 100.0
        for target, source_ids in recommenders.items()
    }
    return sources, support


def _linear_slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    xs = list(range(len(values)))
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(values)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denominator


def persistence_report(
    store: RadarStore,
    run_id: int | None = None,
    *,
    window: int = 5,
    top_n: int = 30,
) -> dict[str, Any]:
    """Measure target persistence across compatible runs.

    Support is normalized per run as the percentage of successful source pages that
    recommended a target. A fixed cohort is strongest because source composition is
    identical across the window; dynamic-search runs are still reported but marked
    as non-fixed.
    """
    if run_id is None:
        run_id = store.latest_run_id()
    if run_id is None:
        raise ValueError("No completed crawl run found")

    run_ids = store.compatible_run_ids(run_id, limit=max(1, window))
    if not run_ids:
        raise ValueError(f"No compatible completed runs found for run #{run_id}")

    seed_sets = [store.seed_ids_for_run(rid) for rid in run_ids]
    fixed_cohort = bool(seed_sets) and all(seed_set == seed_sets[0] for seed_set in seed_sets)
    common_seeds = set.intersection(*seed_sets) if seed_sets else set()
    union_seeds = set.union(*seed_sets) if seed_sets else set()

    support_by_run: dict[int, dict[str, float]] = {}
    source_count_by_run: dict[int, int] = {}
    ranks_by_run: dict[int, defaultdict[str, list[int]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    all_targets: set[str] = set()

    for rid in run_ids:
        edges = store.fetch_edges(rid)
        sources, support = _support_by_target(edges)
        support_by_run[rid] = support
        source_count_by_run[rid] = len(sources)
        rank_map: defaultdict[str, list[int]] = defaultdict(list)
        for edge in edges:
            target = str(edge["target_id"])
            all_targets.add(target)
            rank_map[target].append(max(1, int(edge["rank"])))
            meta[target] = {
                "title": edge.get("target_title") or target,
                "author": edge.get("target_author"),
            }
        ranks_by_run[rid] = rank_map

    rows: list[dict[str, Any]] = []
    for target in all_targets:
        supports = [support_by_run[rid].get(target, 0.0) for rid in run_ids]
        positive_supports = [value for value in supports if value > 0]
        runs_present = len(positive_supports)
        presence_pct = (runs_present / len(run_ids)) * 100.0
        median_support = statistics.median(positive_supports) if positive_supports else 0.0
        median_support_all = statistics.median(supports) if supports else 0.0
        current_support = supports[-1] if supports else 0.0
        slope = _linear_slope(supports)

        per_run_median_ranks = [
            statistics.median(ranks_by_run[rid][target])
            for rid in run_ids
            if ranks_by_run[rid].get(target)
        ]
        median_rank = (
            statistics.median(per_run_median_ranks) if per_run_median_ranks else None
        )

        persistence_score = (presence_pct / 100.0) * median_support
        rows.append(
            {
                "video_id": target,
                "title": meta.get(target, {}).get("title") or target,
                "author": meta.get(target, {}).get("author"),
                "runs_present": runs_present,
                "runs_total": len(run_ids),
                "presence_pct": round(presence_pct, 1),
                "current_support_pct": round(current_support, 1),
                "median_support_when_present_pct": round(median_support, 1),
                "median_support_all_runs_pct": round(median_support_all, 1),
                "max_support_pct": round(max(supports) if supports else 0.0, 1),
                "support_slope_pp_per_run": round(slope, 2) if slope is not None else None,
                "median_recommendation_rank": round(float(median_rank), 1)
                if median_rank is not None
                else None,
                "persistence_score": round(persistence_score, 2),
                "supports_by_run": [round(value, 1) for value in supports],
            }
        )

    rows.sort(
        key=lambda row: (
            row["persistence_score"],
            row["presence_pct"],
            row["current_support_pct"],
        ),
        reverse=True,
    )

    current = store.get_run(run_id)
    return {
        "run": current,
        "run_ids": run_ids,
        "window_requested": max(1, window),
        "runs_used": len(run_ids),
        "fixed_cohort": fixed_cohort,
        "common_seed_count": len(common_seeds),
        "seed_union_count": len(union_seeds),
        "source_counts": [source_count_by_run[rid] for rid in run_ids],
        "signals": rows[:top_n],
    }


def contrast_report(
    store: RadarStore,
    target_run_id: int,
    control_run_ids: list[int],
    *,
    top_n: int = 30,
) -> dict[str, Any]:
    """Contrast one niche run against unrelated control runs.

    Specificity is based on normalized source support. A target that is common in
    the niche but also common in controls is likely generic platform/session noise;
    a target with high niche support and low control support is more niche-specific.
    """
    if not control_run_ids:
        raise ValueError("At least one control run is required")

    target_edges = store.fetch_edges(target_run_id)
    target_sources, target_support = _support_by_target(target_edges)
    if not target_sources:
        raise ValueError(f"Target run #{target_run_id} has no recommendation edges")

    control_supports: list[dict[str, float]] = []
    control_source_counts: list[int] = []
    for rid in control_run_ids:
        edges = store.fetch_edges(rid)
        sources, support = _support_by_target(edges)
        control_source_counts.append(len(sources))
        control_supports.append(support)

    meta: dict[str, dict[str, Any]] = {}
    rank_score: defaultdict[str, float] = defaultdict(float)
    for edge in target_edges:
        target = str(edge["target_id"])
        meta[target] = {
            "title": edge.get("target_title") or target,
            "author": edge.get("target_author"),
        }
        rank = max(1, int(edge["rank"]))
        rank_score[target] += 1.0 / math.log2(rank + 1)

    rows: list[dict[str, Any]] = []
    for target, niche_support in target_support.items():
        controls = [support.get(target, 0.0) for support in control_supports]
        control_avg = statistics.fmean(controls) if controls else 0.0
        control_max = max(controls) if controls else 0.0
        specificity_avg = niche_support - control_avg
        specificity_conservative = niche_support - control_max
        controls_present = sum(1 for value in controls if value > 0)
        rows.append(
            {
                "video_id": target,
                "title": meta.get(target, {}).get("title") or target,
                "author": meta.get(target, {}).get("author"),
                "niche_support_pct": round(niche_support, 1),
                "control_avg_support_pct": round(control_avg, 1),
                "control_max_support_pct": round(control_max, 1),
                "specificity_vs_avg_pp": round(specificity_avg, 1),
                "specificity_vs_max_pp": round(specificity_conservative, 1),
                "controls_present": controls_present,
                "controls_total": len(control_run_ids),
                "rank_score": round(rank_score[target], 3),
            }
        )

    rows.sort(
        key=lambda row: (
            row["specificity_vs_max_pp"],
            row["niche_support_pct"],
            row["rank_score"],
        ),
        reverse=True,
    )

    return {
        "target_run": store.get_run(target_run_id),
        "target_run_id": target_run_id,
        "control_run_ids": control_run_ids,
        "target_source_count": len(target_sources),
        "control_source_counts": control_source_counts,
        "signals": rows[:top_n],
    }
