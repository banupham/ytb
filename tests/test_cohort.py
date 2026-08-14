from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ytb_radar.cohort import (
    cohort_run_label,
    cohort_signature,
    normalize_video_ids,
    read_cohort,
    write_cohort,
)


class CohortHelpersTest(unittest.TestCase):
    def test_normalize_and_signature_are_deterministic(self):
        first = ["B", "A", "B", "C"]
        second = ["C", "B", "A"]
        self.assertEqual(normalize_video_ids(first), ["A", "B", "C"])
        self.assertEqual(cohort_signature(first), cohort_signature(second))
        self.assertEqual(
            cohort_run_label("minecraft", first),
            cohort_run_label("minecraft", second),
        )

    def test_round_trip_cohort_file(self):
        payload = {
            "version": 1,
            "label": "minecraft-core",
            "signature": cohort_signature(["A", "B", "C"]),
            "source_run_id": 9,
            "video_ids": ["C", "A", "B"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cohort.json"
            write_cohort(payload, path)
            loaded = read_cohort(path)
        self.assertEqual(loaded["video_ids"], ["A", "B", "C"])
        self.assertEqual(loaded["label"], "minecraft-core")
        self.assertEqual(loaded["signature"], payload["signature"])


if __name__ == "__main__":
    unittest.main()
