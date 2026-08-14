from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


INSTANCE_DIRECTORY_URL = "https://api.invidious.io/instances.json"
DEFAULT_PROBE_VIDEO_ID = "dQw4w9WgXcQ"


class InvidiousError(RuntimeError):
    """Raised when an Invidious request cannot be completed."""


@dataclass(frozen=True)
class PublicInstance:
    name: str
    uri: str
    region: str | None = None
    api_advertised: bool | None = None
    uptime: float | None = None


@dataclass
class InvidiousClient:
    base_url: str
    region: str = "VN"
    timeout: float = 20.0
    retries: int = 2
    user_agent: str = "ytb-radar/0.2 (+https://github.com/banupham/ytb)"

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


def discover_public_instances(
    directory_url: str = INSTANCE_DIRECTORY_URL,
    timeout: float = 8.0,
) -> list[PublicInstance]:
    """Read the official Invidious instance directory and return usable HTTPS candidates.

    The directory's `api` field is treated as a hint, not as the final health check.
    Some instance metadata can change between directory refreshes, so auto selection
    probes the actual video API before choosing a server.
    """
    req = urllib.request.Request(
        directory_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ytb-radar/0.2 (+https://github.com/banupham/ytb)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise InvidiousError(f"Could not read official instance directory: {exc}") from exc

    if not isinstance(payload, list):
        raise InvidiousError("Unexpected official instance directory response")

    candidates: list[PublicInstance] = []
    for row in payload:
        if not isinstance(row, list) or len(row) != 2:
            continue
        name, info = row
        if not isinstance(name, str) or not isinstance(info, dict):
            continue
        uri = info.get("uri")
        if info.get("type") != "https" or not isinstance(uri, str) or not uri.startswith("https://"):
            continue

        monitor = info.get("monitor") if isinstance(info.get("monitor"), dict) else {}
        if monitor.get("down") is True:
            continue
        uptime_raw = monitor.get("uptime")
        try:
            uptime = float(uptime_raw) if uptime_raw is not None else None
        except (TypeError, ValueError):
            uptime = None

        api_value = info.get("api")
        api_advertised = api_value if isinstance(api_value, bool) else None
        candidates.append(
            PublicInstance(
                name=name,
                uri=uri.rstrip("/"),
                region=info.get("region") if isinstance(info.get("region"), str) else None,
                api_advertised=api_advertised,
                uptime=uptime,
            )
        )

    candidates.sort(
        key=lambda x: (
            x.api_advertised is True,
            x.uptime if x.uptime is not None else -1.0,
        ),
        reverse=True,
    )
    return candidates


def auto_select_client(
    region: str = "VN",
    timeout: float = 20.0,
    directory_url: str = INSTANCE_DIRECTORY_URL,
    probe_video_id: str = DEFAULT_PROBE_VIDEO_ID,
    max_candidates: int = 8,
) -> tuple[InvidiousClient, list[str]]:
    """Select the first official public instance whose video API actually works.

    Returns `(client, diagnostics)`. A manually supplied instance should bypass this
    function so research runs can remain pinned to one backend when repeatability is
    more important than convenience.
    """
    candidates = discover_public_instances(
        directory_url=directory_url,
        timeout=min(max(timeout, 1.0), 10.0),
    )
    if not candidates:
        raise InvidiousError("Official instance directory returned no healthy HTTPS candidates")

    diagnostics: list[str] = []
    for candidate in candidates[: max(1, max_candidates)]:
        probe = InvidiousClient(
            candidate.uri,
            region=region,
            timeout=min(max(timeout, 1.0), 7.0),
            retries=0,
        )
        try:
            video = probe.get_video(probe_video_id)
            if not video.get("videoId"):
                raise InvidiousError("video endpoint returned no videoId")
            diagnostics.append(f"OK {candidate.uri}")
            return (
                InvidiousClient(candidate.uri, region=region, timeout=timeout),
                diagnostics,
            )
        except InvidiousError as exc:
            advertised = "api=yes" if candidate.api_advertised else "api=no/unknown"
            diagnostics.append(f"FAIL {candidate.uri} ({advertised}): {exc}")

    detail = "\n".join(diagnostics)
    raise InvidiousError(
        "No official public Invidious instance currently exposes a working "
        "/api/v1/videos endpoint for this client. Public instances may disable "
        "abusable API endpoints or require anti-bot challenges. Set "
        "YTB_INVIDIOUS_BASE to a self-hosted/known-working instance for reliable "
        f"research.\n{detail}"
    )
