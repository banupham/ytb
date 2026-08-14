from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from ytb_radar.invidious import InvidiousClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class InvidiousClientTest(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_recommendations_reads_documented_field(self, urlopen):
        urlopen.return_value = FakeResponse(
            {
                "videoId": "A",
                "title": "A",
                "recommendedVideos": [
                    {"videoId": "X", "title": "X"},
                    {"videoId": "Y", "title": "Y"},
                ],
            }
        )
        client = InvidiousClient("https://example.invalid", region="VN", retries=0)
        video, recs = client.recommendations("A", limit=1)

        self.assertEqual(video["videoId"], "A")
        self.assertEqual([x["videoId"] for x in recs], ["X"])

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/videos/A", request.full_url)
        self.assertIn("region=VN", request.full_url)


if __name__ == "__main__":
    unittest.main()
