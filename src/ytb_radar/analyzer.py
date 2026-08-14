from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from .store import RadarStore


STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "your", "you", "how",
    "what", "why", "are", "was", "were", "into", "out", "new", "video", "official",
    "của", "và", "là", "cho", "trong", "một", "những", "với", "không", "được",
    "tôi", "bạn", "này", "đó", "khi", "đến", "từ", "trên", "sau", "đang", "làm",
}


def analyze(store: RadarStore, run_id: int | None = None, top_n: int = 20) -> dict[str, Any]:
    if run_id is None:
        run_id = store.latest_run_id()
    if run_id is None:
        raise ValueError("No completed crawl run found")

    edges = store.fetch_edges(run_id)
    run_videos = store.fetch_videos_for_run(run_id)
    videos = {v["video_id"]: v for v in run_videos}
    previous_id = store.previous_compatible_run_id(run_id)
    previous_edges = store.fetch_edges(previous_id) if previous_id is not None else []
    previous_run_videos = (
        store.fetch_videos_for_run(previous_id) if previous_id is not None else []
    )

    directed = nx.DiGraph()
    for video_id, data in videos.items():
        directed.add_node(video_id, **data)
    for edge in edges:
        directed.add_edge(edge["source_id"], edge["target_id"], rank=edge["rank"])

    undirected = directed.to_undirected()
    community_map, communities = _communities(undirected, videos)

    seed_ids = {v["video_id"] for v in run_videos if v.get("role") == "seed"}
    source_ids = {e["source_id"] for e in edges}
    seed_source_success = seed_ids & source_ids

    previous_seed_ids = {
        v["video_id"] for v in previous_run_videos if v.get("role") == "seed"
    }
    previous_source_ids = {e["source_id"] for e in previous_edges}
    common_seed_ids = seed_ids & previous_seed_ids
    comparable_source_ids = (
        common_seed_ids & source_ids & previous_source_ids
        if previous_id is not None
        else set()
    )

    indegree = Counter(edge["target_id"] for edge in edges)
    rank_score: defaultdict[str, float] = defaultdict(float)
    recommenders: defaultdict[str, set[str]] = defaultdict(set)

    for edge in edges:
        target = edge["target_id"]
        rank = max(1, int(edge["rank"]))
        rank_score[target] += 1.0 / math.log2(rank + 1)
        recommenders[target].add(edge["source_id"])

    current_common_indegree = Counter(
        edge["target_id"]
        for edge in edges
        if edge["source_id"] in comparable_source_ids
    )
    previous_common_indegree = Counter(
        edge["target_id"]
        for edge in previous_edges
        if edge["source_id"] in comparable_source_ids
    )

    leaders: list[dict[str, Any]] = []
    for video_id, count in indegree.items():
        meta = videos.get(video_id, {})
        support_rate_pct = (
            round((count / len(source_ids)) * 100, 1) if source_ids else 0.0
        )

        if previous_id is None or not comparable_source_ids:
            prev = None
            current_comparable = None
            delta = None
            growth_pct = None
            comparison_status = "n/a"
        else:
            current_comparable = current_common_indegree.get(video_id, 0)
            prev = previous_common_indegree.get(video_id, 0)
            delta = current_comparable - prev
            if current_comparable == 0 and prev == 0:
                growth_pct = None
                comparison_status = "outside-common"
            elif prev == 0:
                growth_pct = None
                comparison_status = "new"
            else:
                growth_pct = round((delta / prev) * 100, 1)
                comparison_status = "changed"

        leaders.append(
            {
                "video_id": video_id,
                "title": meta.get("title") or video_id,
                "author": meta.get("author"),
                "view_count": meta.get("view_count"),
                "recommended_by": count,
                "support_rate_pct": support_rate_pct,
                "rank_score": round(rank_score[video_id], 3),
                "previous_recommended_by": prev,
                "comparable_current_recommended_by": current_comparable,
                "delta": delta,
                "growth_pct": growth_pct,
                "comparison_status": comparison_status,
                "community": community_map.get(video_id),
                "bridge_score": round(_bridge_score(video_id, undirected, community_map), 3),
            }
        )

    leaders.sort(
        key=lambda x: (x["recommended_by"], x["rank_score"], x["bridge_score"]),
        reverse=True,
    )

    bridge_videos = sorted(
        leaders,
        key=lambda x: (x["bridge_score"], x["recommended_by"]),
        reverse=True,
    )

    run = store.get_run(run_id)
    seed_union = seed_ids | previous_seed_ids
    seed_jaccard_pct = (
        round((len(common_seed_ids) / len(seed_union)) * 100, 1)
        if previous_id is not None and seed_union
        else None
    )
    seed_overlap_current_pct = (
        round((len(common_seed_ids) / len(seed_ids)) * 100, 1)
        if previous_id is not None and seed_ids
        else None
    )

    return {
        "run": run,
        "previous_run_id": previous_id,
        "summary": {
            "videos": len(videos),
            "edges": len(edges),
            "communities": len(communities),
            "sources_crawled": len(source_ids),
            "seeds_found": len(seed_ids),
            "seed_sources_success": len(seed_source_success),
            "seed_sources_failed": len(seed_ids - seed_source_success),
            "seed_fill_pct": (
                round((len(seed_ids) / int(run.get("seed_limit") or 1)) * 100, 1)
                if run
                else None
            ),
            "previous_seeds_found": (
                len(previous_seed_ids) if previous_id is not None else None
            ),
            "seed_overlap": (
                len(common_seed_ids) if previous_id is not None else None
            ),
            "seed_overlap_current_pct": seed_overlap_current_pct,
            "seed_jaccard_pct": seed_jaccard_pct,
            "comparable_seed_sources": len(comparable_source_ids),
        },
        "recommendation_leaders": leaders[:top_n],
        "bridge_candidates": bridge_videos[:top_n],
        "communities": communities,
        "expansion_opportunities": _expansion_opportunities(
            edges, community_map, communities
        )[:top_n],
    }


def _communities(
    graph: nx.Graph, videos: dict[str, dict[str, Any]]
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    if graph.number_of_nodes() == 0:
        return {}, []

    if graph.number_of_edges() == 0:
        raw = [{n} for n in graph.nodes()]
    else:
        raw = list(nx.algorithms.community.greedy_modularity_communities(graph))

    raw.sort(key=len, reverse=True)
    mapping: dict[str, int] = {}
    output: list[dict[str, Any]] = []
    for idx, members in enumerate(raw, start=1):
        for node in members:
            mapping[node] = idx
        titles = [videos.get(node, {}).get("title") or "" for node in members]
        output.append(
            {
                "id": idx,
                "size": len(members),
                "label": _label_from_titles(titles),
                "sample_videos": [
                    {
                        "video_id": node,
                        "title": videos.get(node, {}).get("title") or node,
                    }
                    for node in list(members)[:5]
                ],
            }
        )
    return mapping, output


def _bridge_score(node: str, graph: nx.Graph, community_map: dict[str, int]) -> float:
    if node not in graph:
        return 0.0
    neighbors = list(graph.neighbors(node))
    if not neighbors:
        return 0.0
    own = community_map.get(node)
    cross = sum(1 for other in neighbors if community_map.get(other) != own)
    return cross / len(neighbors)


def _label_from_titles(titles: list[str]) -> str:
    words: Counter[str] = Counter()
    for title in titles:
        for token in re.findall(r"[\wÀ-ỹ]+", title.lower(), flags=re.UNICODE):
            if len(token) < 3 or token.isdigit() or token in STOPWORDS:
                continue
            words[token] += 1
    common = [word for word, _count in words.most_common(3)]
    return " / ".join(common) if common else "unlabeled"


def _expansion_opportunities(
    edges: list[dict[str, Any]],
    community_map: dict[str, int],
    communities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    labels = {c["id"]: c["label"] for c in communities}
    pairs: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

    for edge in edges:
        source_community = community_map.get(edge["source_id"])
        target_community = community_map.get(edge["target_id"])
        if (
            source_community is None
            or target_community is None
            or source_community == target_community
        ):
            continue
        pairs[(source_community, target_community)].append(edge)

    output: list[dict[str, Any]] = []
    for (source_community, target_community), pair_edges in pairs.items():
        pair_edges = sorted(pair_edges, key=lambda e: e["rank"])
        output.append(
            {
                "from_community": source_community,
                "from_label": labels.get(source_community, "unlabeled"),
                "to_community": target_community,
                "to_label": labels.get(target_community, "unlabeled"),
                "cross_edges": len(pair_edges),
                "unique_source_videos": len({e["source_id"] for e in pair_edges}),
                "unique_target_videos": len({e["target_id"] for e in pair_edges}),
                "sample_bridges": [
                    {
                        "source_id": e["source_id"],
                        "source_title": e.get("source_title"),
                        "target_id": e["target_id"],
                        "target_title": e.get("target_title"),
                        "rank": e["rank"],
                    }
                    for e in pair_edges[:5]
                ],
            }
        )

    output.sort(
        key=lambda x: (
            x["cross_edges"],
            x["unique_source_videos"],
            x["unique_target_videos"],
        ),
        reverse=True,
    )
    return output
