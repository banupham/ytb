from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from ytb_radar.invidious import (
    InvidiousClient,
    InvidiousError,
    PublicInstance,
    auto_select_client,
    discover_public_instances,
)


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

    @patch("urllib.request.urlopen")
    def test_discover_public_instances_filters_down_and_non_https(self, urlopen):
        urlopen.return_value = FakeResponse(
            [
                [
                    "good.example",
                    {
                        "uri": "https://good.example",
                        "type": "https",
                        "api": True,
                        "region": "JP",
                        "monitor": {"down": False, "uptime": 99.9},
                    },
                ],
                [
                    "down.example",
                    {
                        "uri": "https://down.example",
                        "type": "https",
                        "api": True,
                        "monitor": {"down": True, "uptime": 99.99},
                    },
                ],
                [
                    "onion.example",
                    {"uri": "http://abc.onion", "type": "onion", "api": True},
                ],
            ]
        )

        rows = discover_public_instances("https://directory.invalid", timeout=1)
        self.assertEqual([x.uri for x in rows], ["https://good.example"])
        self.assertEqual(rows[0].region, "JP")
        self.assertTrue(rows[0].api_advertised)

    @patch("ytb_radar.invidious.discover_public_instances")
    @patch.object(InvidiousClient, "get_video")
    def test_auto_select_falls_back_to_second_candidate(self, get_video, discover):
        discover.return_value = [
            PublicInstance("one", "https://one.example", api_advertised=True, uptime=99.9),
            PublicInstance("two", "https://two.example", api_advertised=False, uptime=99.8),
        ]
        get_video.side_effect = [
            InvidiousError("blocked"),
            {"videoId": "dQw4w9WgXcQ", "recommendedVideos": []},
        ]

        client, diagnostics = auto_select_client(region="VN", timeout=3)
        self.assertEqual(client.base_url, "https://two.example")
        self.assertEqual(len(diagnostics), 2)
        self.assertTrue(diagnostics[0].startswith("FAIL"))
        self.assertTrue(diagnostics[1].startswith("OK"))


if __name__ == "__main__":
    unittest.main()
