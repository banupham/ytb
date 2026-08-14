from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auto_radar import _slug, _summary_text


class AutoRadarHelpersTest(unittest.TestCase):
    def test_slug_is_filesystem_friendly(self):
        self.assertEqual(_slug("nhạc bolero trữ tình"), "nh_c_bolero_tr_t_nh")

    def test_summary_contains_run_and_signal_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = _summary_text(
                stamp="20260814_193000",
                cohort={
                    "label": "minecraft sinh tồn core",
                    "signature": "abc123",
                    "video_ids": ["A", "B"],
                },
                fixed_run_id=12,
                control_runs=[("control one", 13), ("control two", 14)],
                persistence={
                    "signals": [
                        {
                            "runs_present": 2,
                            "runs_total": 2,
                            "current_support_pct": 30.0,
                            "median_support_when_present_pct": 25.0,
                            "support_slope_pp_per_run": 5.0,
                            "title": "Persistent target",
                        }
                    ]
                },
                contrast={
                    "signals": [
                        {
                            "niche_support_pct": 30.0,
                            "control_max_support_pct": 5.0,
                            "specificity_vs_max_pp": 25.0,
                            "controls_present": 1,
                            "controls_total": 2,
                            "title": "Niche target",
                        }
                    ]
                },
                out_dir=Path(tmp),
            )
        self.assertIn("fixed_run=12", text)
        self.assertIn("TOP PERSISTENT SIGNALS", text)
        self.assertIn("Persistent target", text)
        self.assertIn("TOP NICHE-SPECIFIC SIGNALS", text)
        self.assertIn("Niche target", text)


if __name__ == "__main__":
    unittest.main()
