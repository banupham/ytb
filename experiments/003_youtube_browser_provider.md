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

## Status

IMPLEMENTED, LIVE VALIDATION PENDING.

Unit tests can verify provider-independent code and URL parsing, but they do not prove that the current YouTube DOM on the user's network/session will expose stable Watch Next cards. The next user run is the actual experiment.
