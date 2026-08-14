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
  -> search seed videos
  -> youtube.com/watch?v=VIDEO_ID
  -> Watch Next recommendation links
  -> directed recommendation edges
  -> existing SQLite graph/analyzer
```

The CLI defaults to:

```text
--provider youtube
```

The older Invidious provider remains available with:

```text
--provider invidious
```

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

## Root-cause confirmation

The next headed run visually showed normal recommendation videos beside/below the playing YouTube video while the provider still reported `No Watch Next recommendation cards found`.

This confirms the root cause as **selector drift**, not absence of recommendations and not an anti-bot page.

The first implementation depended on classic:

```text
ytd-watch-next-secondary-results-renderer ytd-compact-video-renderer
#related ytd-compact-video-renderer
ytd-compact-video-renderer
```

That assumption is no longer safe for the current YouTube layout.

## Watch Next v2 fix

The provider now treats the stable signal as a normal YouTube watch link:

```text
/watch?v=VIDEO_ID
```

inside the recommendation/secondary area rather than depending on one renderer tag.

Preference order:

```text
#related
-> ytd-watch-next-secondary-results-renderer
-> #secondary
```

Fallback support includes both:

```text
yt-lockup-view-model
ytd-compact-video-renderer
```

If extraction still fails, the provider now prints DOM diagnostics with:

- `#related` count;
- `#secondary` count;
- classic Watch Next renderer count;
- compact renderer count;
- lockup renderer count;
- watch links under related/secondary;
- total watch links on the page;
- current URL and page title.

That makes the next failure directly actionable instead of producing another blind selector guess.

## Next live validation

```bat
git pull
.venv\Scripts\activate
python -m pip install -e .
run_windows.bat bán nhà bình chánh
```

For a smaller visible validation:

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
- further DOM selector drift;
- different Watch Next layout;
- search returns Shorts/shelves instead of ordinary video cards;
- excessive personalization makes repeated graphs unstable;
- recommendation graph is too sparse to infer meaningful communities.

## Status

SEARCH: PASS.

WATCH NEXT V1: FAIL — ROOT CAUSE CONFIRMED AS SELECTOR DRIFT.

WATCH NEXT V2 GENERIC LINK EXTRACTION: IMPLEMENTED, LIVE VALIDATION PENDING.
