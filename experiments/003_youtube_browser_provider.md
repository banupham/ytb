# Experiment 003 — Direct YouTube browser provider

Date: 2026-08-14

## Trigger

A real Windows run using the query `bán nhà bình chánh` successfully installed YTB Radar and reached automatic Invidious selection, but every public candidate failed before the query was executed:

- multiple `/api/v1/videos/:id` requests returned HTTP 403;
- one returned HTTP 401;
- one timed out;
- one Yggdrasil-only hostname could not resolve on the normal network.

This is evidence that public Invidious API availability is not reliable enough to be the only provider for the project.

## Hypothesis

A normal Chromium browser loading youtube.com can provide a usable observation of:

1. YouTube search results for seed discovery;
2. Watch Next recommendation cards for each source video.

If these observations can be collected repeatedly, the existing SQLite + graph analyzer does not need to change.

## Implementation

Version 0.2 adds `YouTubeBrowserProvider` using Playwright.

Default flow:

```text
query
  -> youtube.com/results
  -> ytd-video-renderer seeds
  -> youtube.com/watch?v=VIDEO_ID
  -> Watch Next ytd-compact-video-renderer cards
  -> directed recommendation edges
  -> existing SQLite graph/analyzer
```

The CLI now defaults to:

```text
--provider youtube
```

The older Invidious provider remains available with:

```text
--provider invidious
```

## First live validation command

```bat
git pull
.venv\Scripts\activate
python -m pip install -e .
python -m ytb_radar ping
run_windows.bat bán nhà bình chánh
```

If headless YouTube is challenged or renders differently:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --headed ^
  --query "bán nhà bình chánh" ^
  --seed-limit 5 ^
  --depth 0 ^
  --recs 10 ^
  --delay 1.5
```

## Success criteria

PASS only if a real Windows run produces all of the following:

- at least 5 search seed video IDs;
- at least 5 source watch pages with extracted recommendations;
- at least 30 total recommendation edges;
- at least one recommendation target referenced by two or more distinct source videos;
- analyzer completes without fabricated data.

Stronger evidence would be repeated runs where major hubs/communities recur.

## Failure modes to record

- YouTube anti-bot/challenge page;
- consent page not dismissed;
- DOM selector drift;
- different Watch Next layout;
- search returns Shorts/shelves instead of ordinary video cards;
- excessive personalization makes repeated graphs unstable;
- recommendation graph is too sparse to infer meaningful communities.

## Live validation #1 — Windows, query `bán nhà bình chánh`

Observed output:

```text
Provider: YouTube browser (headless, channel=auto, region=VN)
WARN provider failed for bts4RmP0KZw: No Watch Next recommendation cards found for bts4RmP0KZw
WARN provider failed for yB-Ured3k1U: No Watch Next recommendation cards found for yB-Ured3k1U
WARN provider failed for WRDNuj9GAZA: No Watch Next recommendation cards found for WRDNuj9GAZA
WARN provider failed for oXcLKbjQIFQ: No Watch Next recommendation cards found for oXcLKbjQIFQ
WARN provider failed for DgTJ9Q7igU4: No Watch Next recommendation cards found for DgTJ9Q7igU4
WARN provider failed for J7dA-qYHh18: No Watch Next recommendation cards found for J7dA-qYHh18
WARN provider failed for Sj_QlYZpZAE: No Watch Next recommendation cards found for Sj_QlYZpZAE
WARN provider failed for 9X8bpuRbSUM: No Watch Next recommendation cards found for 9X8bpuRbSUM
crawl complete: run_id=1
RUN #1 | query='bán nhà bình chánh' | status=done
videos=8 edges=0 sources=0 communities=8
```

Interpretation:

- Search seed extraction succeeded: 8 real YouTube video IDs were discovered from the query.
- The browser successfully navigated far enough that the provider attempted each seed watch page.
- Watch Next extraction failed for all 8 seed videos.
- Therefore `edges=0` and `sources=0`; no recommendation graph was observed.
- The 8 reported communities are singleton seed nodes only and are not meaningful audience/recommendation communities.
- `status=done` is misleading for this run because the crawler currently tolerates provider failures per source and still closes the run as done. A later revision should distinguish `done`, `partial`, and `failed/no_edges`.

Likely failure class from the current evidence: Watch Next DOM/renderer mismatch or content not rendered by the time the current selectors are checked. The current provider looks specifically for `ytd-compact-video-renderer` under Watch Next/related containers, so the next diagnostic must inspect the actual headed DOM instead of guessing another selector.

Result: **FAIL** against Experiment 003 success criteria.

## Status

LIVE VALIDATION #1 FAILED AT WATCH NEXT EXTRACTION.

The search half of BrowserProvider is proven on the user's Windows/network context. The recommendation half is not yet proven. Next step: run headed with a small seed set and inspect/save the actual watch-page DOM or network response that contains recommended video IDs.
