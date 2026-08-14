from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ytb_radar.analyzer import analyze
from ytb_radar.crawler import CrawlConfig, RecommendationCrawler
from ytb_radar.store import RadarStore


class FakeClient:
    base_url = "https://fake.invalid"
    region = "VN"

    def __init__(self, graph: dict[str, list[str]]) -> None:
        self.graph = graph

    def search_videos(self, query: str, limit: int = 20):
        return [self._meta(video_id) for video_id in list(self.graph)[:limit]]

    def recommendations(self, video_id: str, limit: int = 20):
        rec_ids = self.graph.get(video_id, [])[:limit]
        return self._meta(video_id), [self._meta(x) for x in rec_ids]

    @staticmethod
    def _meta(video_id: str):
        return {
            "type": "video",
            "videoId": video_id,
            "title": f"Topic {video_id}",
            "author": f"Channel {video_id[0]}",
            "authorId": f"UC-{video_id[0]}",
            "viewCount": 1000,
            "published": 1700000000,
            "lengthSeconds": 600,
        }


class RadarTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "radar.db")
        self.store = RadarStore(self.db)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_crawl_builds_recommendation_edges(self):
        graph = {
            "A": ["X", "Y", "Z"],
            "B": ["X", "Y", "W"],
            "C": ["X", "Q", "R"],
        }
        crawler = RecommendationCrawler(
            FakeClient(graph),
            self.store,
            CrawlConfig(seed_limit=3, depth=0, recs_per_video=3, max_videos=10, delay=0),
        )
        run_id = crawler.scan_query("topic")
        edges = self.store.fetch_edges(run_id)

        self.assertEqual(len(edges), 9)
        x_sources = {e["source_id"] for e in edges if e["target_id"] == "X"}
        self.assertEqual(x_sources, {"A", "B", "C"})

    def test_analyzer_finds_recommendation_hub_and_seed_coverage(self):
        graph = {
            "A": ["X", "Y"],
            "B": ["X", "Z"],
            "C": [],
        }
        crawler = RecommendationCrawler(
            FakeClient(graph),
            self.store,
            CrawlConfig(seed_limit=3, depth=0, recs_per_video=2, max_videos=10, delay=0),
        )
        run_id = crawler.scan_query("topic")
        report = analyze(self.store, run_id, top_n=5)

        leader = report["recommendation_leaders"][0]
        self.assertEqual(leader["video_id"], "X")
        self.assertEqual(leader["recommended_by"], 2)
        self.assertEqual(leader["support_rate_pct"], 100.0)
        self.assertEqual(report["summary"]["edges"], 4)
        self.assertEqual(report["summary"]["seeds_found"], 3)
        self.assertEqual(report["summary"]["seed_sources_success"], 2)
        self.assertEqual(report["summary"]["seed_sources_failed"], 1)

    def test_analyzer_compares_only_compatible_runs(self):
        config = CrawlConfig(seed_limit=3, depth=0, recs_per_video=2, max_videos=10, delay=0)
        first = RecommendationCrawler(
            FakeClient({"A": ["X", "Y"], "B": ["X", "Z"], "C": ["Q", "W"]}),
            self.store,
            config,
        ).scan_query("topic")

        second = RecommendationCrawler(
            FakeClient({"A": ["X", "Y"], "B": ["X", "Z"], "C": ["X", "W"]}),
            self.store,
            config,
        ).scan_query("topic")

        report = analyze(self.store, second, top_n=10)
        x = next(x for x in report["recommendation_leaders"] if x["video_id"] == "X")
        self.assertEqual(report["previous_run_id"], first)
        self.assertEqual(report["summary"]["seed_overlap"], 3)
        self.assertEqual(report["summary"]["comparable_seed_sources"], 3)
        self.assertEqual(x["previous_recommended_by"], 2)
        self.assertEqual(x["comparable_current_recommended_by"], 3)
        self.assertEqual(x["delta"], 1)
        self.assertEqual(x["growth_pct"], 50.0)

        third = RecommendationCrawler(
            FakeClient({"A": ["X", "Y"], "B": ["X", "Z"], "C": ["X", "W"]}),
            self.store,
            config,
        ).scan_query("different topic")
        third_report = analyze(self.store, third, top_n=10)
        self.assertIsNone(third_report["previous_run_id"])
        third_x = next(x for x in third_report["recommendation_leaders"] if x["video_id"] == "X")
        self.assertIsNone(third_x["previous_recommended_by"])
        self.assertIsNone(third_x["growth_pct"])

    def test_seed_set_change_does_not_create_false_growth(self):
        config = CrawlConfig(seed_limit=3, depth=0, recs_per_video=2, max_videos=10, delay=0)
        first = RecommendationCrawler(
            FakeClient({"A": ["X", "Y"], "B": ["X", "Z"], "C": ["Q", "W"]}),
            self.store,
            config,
        ).scan_query("stable")

        # The new third seed D also recommends X. Raw refs rise 2 -> 3, but A/B are
        # the only common successful seed sources and they did not change.
        second = RecommendationCrawler(
            FakeClient({"A": ["X", "Y"], "B": ["X", "Z"], "D": ["X", "W"]}),
            self.store,
            config,
        ).scan_query("stable")

        report = analyze(self.store, second, top_n=10)
        x = next(x for x in report["recommendation_leaders"] if x["video_id"] == "X")
        self.assertEqual(report["previous_run_id"], first)
        self.assertEqual(report["summary"]["seed_overlap"], 2)
        self.assertEqual(report["summary"]["comparable_seed_sources"], 2)
        self.assertEqual(x["recommended_by"], 3)
        self.assertEqual(x["previous_recommended_by"], 2)
        self.assertEqual(x["comparable_current_recommended_by"], 2)
        self.assertEqual(x["growth_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
