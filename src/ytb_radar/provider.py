from __future__ import annotations

from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Raised when a recommendation data provider cannot complete a request."""


class RecommendationProvider(Protocol):
    """Minimal interface consumed by RecommendationCrawler."""

    base_url: str
    region: str

    def search_videos(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        ...

    def recommendations(
        self, video_id: str, limit: int = 20
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        ...
