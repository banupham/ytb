from __future__ import annotations

import unittest

from ytb_radar.youtube_browser import YouTubeBrowserProvider, extract_video_id


class YouTubeBrowserHelpersTest(unittest.TestCase):
    def test_extract_video_id_from_watch_url(self):
        self.assertEqual(
            extract_video_id("/watch?v=dQw4w9WgXcQ&pp=abc"),
            "dQw4w9WgXcQ",
        )

    def test_extract_video_id_from_absolute_url(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=abcDEF_1234"),
            "abcDEF_1234",
        )

    def test_extract_video_id_from_youtu_be(self):
        self.assertEqual(
            extract_video_id("https://youtu.be/abcDEF_1234?t=12"),
            "abcDEF_1234",
        )

    def test_non_video_url_returns_none(self):
        self.assertIsNone(extract_video_id("https://www.youtube.com/@example"))

    def test_run_identity_distinguishes_isolated_and_shared_sessions(self):
        isolated = YouTubeBrowserProvider(isolate_watch_context=True)
        shared = YouTubeBrowserProvider(isolate_watch_context=False)
        self.assertIn("isolated-watch", isolated.run_identity)
        self.assertIn("shared-session", shared.run_identity)
        self.assertNotEqual(isolated.run_identity, shared.run_identity)


if __name__ == "__main__":
    unittest.main()
