from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ytb_radar.crawler import CrawlConfig, RecommendationCrawler
from ytb_radar.signals import contrast_report, persistence_report
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
        }


class SignalAnalysisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "radar.db")
        self.store = RadarStore(self.db)
        self.config = CrawlConfig(
            seed_limit=3,
            depth=0,
            recs_per_video=3,
            max_videos=10,
            delay=0,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, query: str, graph: dict[str, list[str]]) -> int:
        return RecommendationCrawler(
            FakeClient(graph), self.store, self.config
        ).scan_query(query)

    def test_persistence_report_tracks_fixed_seed_history(self):
        self._run(
            "minecraft",
            {"A": ["X", "Y"], "B": ["X"], "C": ["Z"]},
        )
        self._run(
            "minecraft",
            {"A": ["X", "Y"], "B": ["X"], "C": ["X", "Z"]},
        )
        latest = self._run(
            "minecraft",
            {"A": ["X"], "B": ["X", "W"], "C": ["X", "Z"]},
        )

        report = persistence_report(self.store, latest, window=5, top_n=10)
        self.assertEqual(report["run_ids"], [1, 2, 3])
        self.assertTrue(report["fixed_cohort"])
        x = next(row for row in report["signals"] if row["video_id"] == "X")
        self.assertEqual(x["runs_present"], 3)
        self.assertEqual(x["presence_pct"], 100.0)
        self.assertEqual(x["current_support_pct"], 100.0)
        self.assertGreater(x["support_slope_pp_per_run"], 0)

    def test_contrast_demotes_generic_control_target(self):
        target = self._run(
            "minecraft",
            {"A": ["X", "G"], "B": ["X", "G"], "C": ["X"]},
        )
        control = self._run(
            "real-estate",
            {"D": ["G"], "E": ["G"], "F": ["G"]},
        )

        report = contrast_report(
            self.store, target_run_id=target, control_run_ids=[control], top_n=10
        )
        x = next(row for row in report["signals"] if row["video_id"] == "X")
        generic = next(row for row in report["signals"] if row["video_id"] == "G")
        self.assertEqual(x["niche_support_pct"], 100.0)
        self.assertEqual(x["control_max_support_pct"], 0.0)
        self.assertGreater(x["specificity_vs_max_pp"], generic["specificity_vs_max_pp"])
        self.assertLess(generic["specificity_vs_max_pp"], 0)


if __name__ == "__main__":
    unittest.main()
