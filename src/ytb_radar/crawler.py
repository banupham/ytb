from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable

from .provider import ProviderError, RecommendationProvider
from .store import RadarStore


@dataclass
class CrawlConfig:
    seed_limit: int = 20
    depth: int = 1
    recs_per_video: int = 20
    max_videos: int = 200
    delay: float = 0.4


class RecommendationCrawler:
    def __init__(
        self,
        client: RecommendationProvider,
        store: RadarStore,
        config: CrawlConfig,
    ) -> None:
        self.client = client
        self.store = store
        self.config = config

    def scan_query(self, query: str) -> int:
        seeds = self.client.search_videos(query, self.config.seed_limit)
        return self.scan_seed_items(seeds, query=query)

    def scan_video_ids(self, video_ids: Iterable[str], query: str | None = None) -> int:
        seeds = [{"videoId": video_id, "title": video_id} for video_id in video_ids]
        return self.scan_seed_items(seeds, query=query)

    def scan_seed_items(self, seeds: list[dict[str, Any]], query: str | None = None) -> int:
        provider_identity = str(
            getattr(self.client, "run_identity", None) or self.client.base_url
        )
        run_id = self.store.start_run(
            query=query,
            region=self.client.region,
            instance=provider_identity,
            seed_limit=self.config.seed_limit,
            depth=self.config.depth,
            recs_per_video=self.config.recs_per_video,
            max_videos=self.config.max_videos,
        )

        queue: deque[tuple[str, int, str]] = deque()
        queued: set[str] = set()
        fetched: set[str] = set()

        try:
            for item in seeds[: self.config.seed_limit]:
                video_id = str(item.get("videoId") or "")
                if not video_id or video_id in queued:
                    continue
                self.store.upsert_video(item)
                self.store.mark_run_video(run_id, video_id, 0, "seed")
                queue.append((video_id, 0, "seed"))
                queued.add(video_id)

            while queue and len(fetched) < self.config.max_videos:
                source_id, depth, _role = queue.popleft()
                if source_id in fetched:
                    continue

                try:
                    video, recs = self.client.recommendations(
                        source_id, self.config.recs_per_video
                    )
                except ProviderError as exc:
                    print(f"WARN provider failed for {source_id}: {exc}")
                    fetched.add(source_id)
                    continue

                self.store.upsert_video(video)
                self.store.mark_run_video(
                    run_id,
                    source_id,
                    depth,
                    "seed" if depth == 0 else "expanded",
                )

                for rank, rec in enumerate(recs, start=1):
                    target_id = str(rec.get("videoId") or "")
                    if not target_id or target_id == source_id:
                        continue
                    self.store.upsert_video(rec)
                    self.store.mark_run_video(run_id, target_id, depth + 1, "recommended")
                    self.store.add_edge(run_id, source_id, target_id, rank)

                    if (
                        depth < self.config.depth
                        and target_id not in queued
                        and target_id not in fetched
                        and len(queued) < self.config.max_videos * 2
                    ):
                        queue.append((target_id, depth + 1, "expanded"))
                        queued.add(target_id)

                fetched.add(source_id)
                if self.config.delay > 0 and queue:
                    time.sleep(self.config.delay)

            self.store.finish_run(run_id, "done")
            return run_id
        except Exception as exc:
            self.store.finish_run(run_id, "failed", str(exc))
            raise
