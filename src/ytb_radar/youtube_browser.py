from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from .provider import ProviderError


def extract_video_id(href: str | None) -> str | None:
    if not href:
        return None
    try:
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc in {"youtu.be", "www.youtu.be"}:
            value = parsed.path.strip("/").split("/")[0]
            return value or None
        query = urllib.parse.parse_qs(parsed.query)
        value = query.get("v", [None])[0]
        if value:
            return str(value)
    except Exception:
        return None
    match = re.search(r"(?:\?|&)v=([A-Za-z0-9_-]{6,})", href)
    return match.group(1) if match else None


@dataclass
class YouTubeBrowserProvider:
    """Observe YouTube search and Watch Next recommendations in a real browser.

    By default each watch page is opened in a fresh browser context. This prevents
    the crawler's earlier seed visits from training the same temporary YouTube
    session and contaminating later Watch Next observations.
    """

    region: str = "VN"
    timeout: float = 20.0
    headless: bool = True
    browser_channel: str = "auto"
    locale: str = "vi-VN"
    isolate_watch_context: bool = True
    base_url: str = "https://www.youtube.com"
    _playwright: Any = field(default=None, init=False, repr=False)
    _browser: Any = field(default=None, init=False, repr=False)
    _context: Any = field(default=None, init=False, repr=False)
    _page: Any = field(default=None, init=False, repr=False)
    _active_channel: str | None = field(default=None, init=False)

    @property
    def run_identity(self) -> str:
        mode = "isolated-watch" if self.isolate_watch_context else "shared-session"
        return f"youtube-browser:{mode}:{self.base_url}"

    def _make_context_page(self) -> tuple[Any, Any]:
        if self._browser is None:
            raise ProviderError("Browser is not started")
        context = self._browser.new_context(
            locale=self.locale,
            viewport={"width": 1440, "height": 1000},
        )
        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"image", "media", "font"}
            else route.continue_(),
        )
        page = context.new_page()
        page.set_default_timeout(max(1000, int(self.timeout * 1000)))
        return context, page

    def _start(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ProviderError(
                "Playwright is not installed. Run: python -m pip install -e ."
            ) from exc

        self._playwright = sync_playwright().start()
        requested = self.browser_channel or os.environ.get("YTB_BROWSER_CHANNEL", "auto")
        channels = [requested] if requested != "auto" else ["chrome", "msedge", None]
        errors: list[str] = []
        for channel in channels:
            try:
                kwargs: dict[str, Any] = {"headless": self.headless}
                if channel:
                    kwargs["channel"] = channel
                self._browser = self._playwright.chromium.launch(**kwargs)
                self._active_channel = channel or "chromium"
                break
            except PlaywrightError as exc:
                errors.append(f"{channel or 'chromium'}: {exc}")

        if self._browser is None:
            self.close()
            raise ProviderError(
                "Could not launch Chrome/Edge/Chromium with Playwright. "
                "Install Google Chrome or Microsoft Edge, or run `playwright install chromium`. "
                + " | ".join(errors)
            )

        self._context, self._page = self._make_context_page()

    def close(self) -> None:
        for obj in (self._context, self._browser):
            if obj is not None:
                try:
                    obj.close()
                except Exception:
                    pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def __enter__(self) -> "YouTubeBrowserProvider":
        self._start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _url(self, path: str, params: dict[str, str]) -> str:
        query = dict(params)
        query.setdefault("hl", "vi")
        query.setdefault("gl", self.region)
        return f"{self.base_url}{path}?{urllib.parse.urlencode(query)}"

    def _goto(self, url: str) -> None:
        self._start()
        try:
            self._page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=max(1000, int(self.timeout * 1000)),
            )
            self._dismiss_consent_if_present()
            self._detect_block_page()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Browser navigation failed for {url}: {exc}") from exc

    def _dismiss_consent_if_present(self) -> None:
        candidates = [
            "button:has-text('Reject all')",
            "button:has-text('Từ chối tất cả')",
            "button:has-text('Accept all')",
            "button:has-text('Chấp nhận tất cả')",
        ]
        for selector in candidates:
            try:
                button = self._page.locator(selector).first
                if button.is_visible(timeout=500):
                    button.click(timeout=1000)
                    self._page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    def _detect_block_page(self) -> None:
        try:
            body = (self._page.locator("body").inner_text(timeout=1500) or "").lower()
        except Exception:
            return
        markers = [
            "sign in to confirm you're not a bot",
            "sign in to confirm you’re not a bot",
            "unusual traffic",
            "xác nhận bạn không phải là bot",
        ]
        if any(marker in body for marker in markers):
            raise ProviderError(
                "YouTube returned an anti-bot/challenge page for the browser session. "
                "Try `--headed`, reduce crawl speed, or use a normal browser profile in a later provider version."
            )

    def stats(self) -> dict[str, Any]:
        self._goto(self._url("/", {}))
        return {
            "provider": "youtube-browser",
            "baseUrl": self.base_url,
            "region": self.region,
            "browserChannel": self._active_channel,
            "headless": self.headless,
            "isolateWatchContext": self.isolate_watch_context,
        }

    def _collect_search_results(
        self,
        selector: str,
        results: list[dict[str, Any]],
        seen: set[str],
        limit: int,
    ) -> None:
        for card in self._page.locator(selector).all():
            if len(results) >= limit:
                return
            try:
                title_link = card.locator("a#video-title").first
                href = title_link.get_attribute("href")
                video_id = extract_video_id(href)
                if not video_id or video_id in seen:
                    continue
                title = (
                    title_link.get_attribute("title")
                    or title_link.inner_text()
                    or ""
                ).strip()
                author = None
                try:
                    author = (
                        card.locator("ytd-channel-name a").first.inner_text(timeout=700)
                        or ""
                    ).strip() or None
                except Exception:
                    pass
                results.append(
                    {
                        "type": "video",
                        "videoId": video_id,
                        "title": title or video_id,
                        "author": author,
                        "source": "youtube-browser-search",
                    }
                )
                seen.add(video_id)
            except Exception:
                continue

    def search_videos(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        self._goto(self._url("/results", {"search_query": query}))
        selector = "ytd-video-renderer"
        try:
            self._page.locator(selector).first.wait_for(
                state="attached", timeout=max(1500, int(self.timeout * 1000))
            )
        except Exception:
            self._detect_block_page()
            raise ProviderError(f"YouTube search returned no video results for query: {query}")

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        stagnant_rounds = 0

        # YouTube search lazy-loads more ordinary video cards while scrolling. The
        # previous implementation only read the first DOM batch, which made an
        # identical seed_limit produce 12 seeds in one run and 15 in another.
        for _round in range(10):
            before = len(results)
            self._collect_search_results(selector, results, seen, limit)
            if len(results) >= limit:
                break

            if len(results) == before:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0
            if stagnant_rounds >= 2:
                break

            try:
                self._page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                self._page.wait_for_timeout(900)
            except Exception:
                break

        if not results:
            raise ProviderError(
                f"Could not extract YouTube video IDs from search results: {query}"
            )
        return results

    def _wait_for_watch_next_links(self) -> None:
        try:
            self._page.wait_for_function(
                """
                () => Boolean(document.querySelector(
                    '#related a[href*="/watch?v="], ' +
                    'ytd-watch-next-secondary-results-renderer a[href*="/watch?v="], ' +
                    '#secondary a[href*="/watch?v="], ' +
                    'yt-lockup-view-model a[href*="/watch?v="], ' +
                    'ytd-compact-video-renderer a[href*="/watch?v="]'
                ))
                """,
                timeout=max(3000, min(int(self.timeout * 1000), 10000)),
            )
        except Exception:
            pass

    def _watch_next_records(self) -> list[dict[str, Any]]:
        return self._page.evaluate(
            """
            () => {
              const rootSelectors = [
                '#related',
                'ytd-watch-next-secondary-results-renderer',
                '#secondary'
              ];

              let root = null;
              for (const selector of rootSelectors) {
                const candidate = document.querySelector(selector);
                if (candidate && candidate.querySelector('a[href*="/watch?v="]')) {
                  root = candidate;
                  break;
                }
              }

              let anchors = [];
              if (root) {
                anchors = Array.from(root.querySelectorAll('a[href*="/watch?v="]'));
              } else {
                anchors = Array.from(document.querySelectorAll(
                  'yt-lockup-view-model a[href*="/watch?v="], ' +
                  'ytd-compact-video-renderer a[href*="/watch?v="], ' +
                  'ytd-video-renderer a[href*="/watch?v="]'
                ));
              }

              const records = [];
              for (const anchor of anchors) {
                const href = anchor.getAttribute('href');
                if (!href) continue;

                const card = anchor.closest(
                  'yt-lockup-view-model, ' +
                  'ytd-compact-video-renderer, ' +
                  'ytd-video-renderer, ' +
                  'ytd-rich-item-renderer, ' +
                  'ytd-playlist-panel-video-renderer'
                ) || anchor.parentElement;

                const titleEl = card ? card.querySelector(
                  'a#video-title, #video-title, h3 a, h3, ' +
                  '.yt-lockup-metadata-view-model__title, ' +
                  '[class*="lockup-metadata-view-model__title"]'
                ) : null;
                const authorEl = card ? card.querySelector(
                  'ytd-channel-name a, #channel-name a, #channel-name, ' +
                  'a[href^="/@"], a[href^="/channel/"]'
                ) : null;

                const title = (
                  (titleEl && (titleEl.getAttribute('title') || titleEl.textContent)) ||
                  anchor.getAttribute('title') ||
                  anchor.getAttribute('aria-label') ||
                  ''
                ).trim();
                const author = authorEl ? (authorEl.textContent || '').trim() : '';

                records.push({href, title, author});
              }
              return records;
            }
            """
        )

    def _watch_next_diagnostics(self) -> dict[str, Any]:
        try:
            return self._page.evaluate(
                """
                () => ({
                  related: document.querySelectorAll('#related').length,
                  secondary: document.querySelectorAll('#secondary').length,
                  classicWatchNext: document.querySelectorAll('ytd-watch-next-secondary-results-renderer').length,
                  compactCards: document.querySelectorAll('ytd-compact-video-renderer').length,
                  lockupCards: document.querySelectorAll('yt-lockup-view-model').length,
                  relatedWatchLinks: document.querySelectorAll('#related a[href*="/watch?v="]').length,
                  secondaryWatchLinks: document.querySelectorAll('#secondary a[href*="/watch?v="]').length,
                  allWatchLinks: document.querySelectorAll('a[href*="/watch?v="]').length,
                  pageTitle: document.title,
                  url: location.href
                })
                """
            )
        except Exception as exc:
            return {"diagnostic_error": str(exc)}

    def _recommendations_on_current_page(
        self, video_id: str, limit: int
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        self._goto(self._url("/watch", {"v": video_id}))

        title = video_id
        author = None
        try:
            title = (
                self._page.locator(
                    "ytd-watch-metadata h1 yt-formatted-string"
                ).first.inner_text(timeout=2500)
                or video_id
            ).strip()
        except Exception:
            try:
                title = (
                    self._page.locator("h1 yt-formatted-string")
                    .first.inner_text(timeout=1000)
                    or video_id
                ).strip()
            except Exception:
                pass
        try:
            author = (
                self._page.locator(
                    "ytd-watch-metadata ytd-channel-name a"
                ).first.inner_text(timeout=1500)
                or ""
            ).strip() or None
        except Exception:
            pass

        source = {
            "type": "video",
            "videoId": video_id,
            "title": title,
            "author": author,
            "source": "youtube-browser-watch",
        }

        self._wait_for_watch_next_links()
        raw_records = self._watch_next_records()

        recs: list[dict[str, Any]] = []
        seen: set[str] = {video_id}
        for record in raw_records:
            if len(recs) >= limit:
                break
            target_id = extract_video_id(record.get("href"))
            if not target_id or target_id in seen:
                continue
            title_text = str(record.get("title") or "").strip()
            rec_author = str(record.get("author") or "").strip() or None
            recs.append(
                {
                    "type": "video",
                    "videoId": target_id,
                    "title": title_text or target_id,
                    "author": rec_author,
                    "source": "youtube-browser-watch-next",
                }
            )
            seen.add(target_id)

        if not recs:
            self._detect_block_page()
            diagnostics = self._watch_next_diagnostics()
            raise ProviderError(
                f"Watch Next is visible but no recommendation video IDs were extracted "
                f"for {video_id}. DOM diagnostics: {diagnostics}"
            )
        return source, recs

    def recommendations(
        self, video_id: str, limit: int = 20
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        self._start()
        if not self.isolate_watch_context:
            return self._recommendations_on_current_page(video_id, limit)

        original_context = self._context
        original_page = self._page
        temp_context = None
        try:
            temp_context, temp_page = self._make_context_page()
            self._context = temp_context
            self._page = temp_page
            return self._recommendations_on_current_page(video_id, limit)
        finally:
            if temp_context is not None:
                try:
                    temp_context.close()
                except Exception:
                    pass
            self._context = original_context
            self._page = original_page
