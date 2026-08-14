from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class InvidiousError(RuntimeError):
    """Raised when an Invidious request cannot be completed."""


@dataclass
class InvidiousClient:
    base_url: str
    region: str = "VN"
    timeout: float = 20.0
    retries: int = 2
    user_agent: str = "ytb-radar/0.1 (+https://github.com/banupham/ytb)"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = dict(params or {})
        if self.region and "region" not in query:
            query["region"] = self.region
        url = f"{self.base_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query, doseq=True)

        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.6 * (2**attempt))
                    continue
                break
        raise InvidiousError(f"GET {url} failed: {last_error}") from last_error

    def stats(self) -> dict[str, Any]:
        data = self._get_json("/api/v1/stats", {})
        if not isinstance(data, dict):
            raise InvidiousError("Unexpected /api/v1/stats response")
        return data

    def search_videos(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        results: list[dict[str, Any]] = []
        page = 1
        while len(results) < limit:
            batch = self._get_json(
                "/api/v1/search",
                {
                    "q": query,
                    "page": page,
                    "type": "video",
                },
            )
            if not isinstance(batch, list) or not batch:
                break

            for item in batch:
                if isinstance(item, dict) and item.get("type") == "video" and item.get("videoId"):
                    results.append(item)
                    if len(results) >= limit:
                        break
            page += 1
            if page > 10:
                break
        return results

    def get_video(self, video_id: str) -> dict[str, Any]:
        data = self._get_json(f"/api/v1/videos/{urllib.parse.quote(video_id)}")
        if not isinstance(data, dict):
            raise InvidiousError(f"Unexpected video response for {video_id}")
        return data

    def recommendations(self, video_id: str, limit: int = 20) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        video = self.get_video(video_id)
        recs = video.get("recommendedVideos") or []
        if not isinstance(recs, list):
            recs = []
        return video, [x for x in recs[: max(0, limit)] if isinstance(x, dict) and x.get("videoId")]
