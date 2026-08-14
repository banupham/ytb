# YTB Radar

Experimental **YouTube recommendation graph radar**. It repeatedly observes YouTube recommendations, stores a directed graph, measures change over time, detects communities/bridges, and turns those observations into testable audience-expansion hypotheses for creators.

The project does **not** claim to reverse-engineer or guarantee YouTube recommendations.

## Providers

YTB Radar now has two interchangeable recommendation providers:

```text
RecommendationProvider
        |
        +-- youtube   -> real youtube.com page through Playwright
        |
        +-- invidious -> /api/v1/videos/:id when an API-enabled instance exists
        |
        v
      Crawler -> SQLite -> Graph analyzer
```

`youtube` is the default because the public Invidious instances tested on 2026-08-14 rejected, disabled, timed out, or otherwise did not expose the video API needed by the project.

A browser observation means: **this browser/session/context saw B in Watch Next while viewing A at crawl time**. It does not mean every viewer sees B.

## Current capabilities

- Search YouTube for seed videos from a query.
- Start from explicit YouTube video IDs.
- Read Watch Next recommendation cards from a real YouTube watch page.
- Optional Invidious provider remains available.
- Store each crawl in SQLite.
- Build directed edges `source video -> recommended video`.
- Rank recommendation hubs by number of unique recommending sources and position-weighted score.
- Compare completed runs to measure expansion/contraction.
- Detect graph communities.
- Find bridge candidates between communities.
- Rank cross-community audience-expansion opportunities.
- Export analysis as JSON.

## Requirements

- Windows/Linux/macOS with Python 3.10+.
- Google Chrome or Microsoft Edge is recommended for the browser provider.
- Network access to YouTube.

Playwright can control installed Chrome/Edge. If neither is installed, install Playwright Chromium with:

```bat
playwright install chromium
```

## Install on Windows

```bat
git clone https://github.com/banupham/ytb.git
cd ytb
py -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

Check the direct YouTube provider:

```bat
python -m ytb_radar ping
```

Expected shape:

```json
{
  "provider": "youtube-browser",
  "baseUrl": "https://www.youtube.com",
  "region": "VN",
  "browserChannel": "chrome",
  "headless": true
}
```

## First real experiment

The easiest Windows command is:

```bat
run_windows.bat bán nhà bình chánh
```

Equivalent explicit command:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --query "bán nhà bình chánh" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 1 ^
  --recs 20 ^
  --max-videos 200 ^
  --delay 0.8
```

The flow is:

```text
"bán nhà bình chánh"
        |
        v
YouTube search page
        |
        v
~20 seed videos
        |
        v
open each watch page
        |
        v
Watch Next recommendations
        |
        v
A -> B,C,D...
        |
        v
SQLite recommendation graph
        |
        +--> hubs
        +--> communities
        +--> bridges
        +--> expansion opportunities
```

Run the same query again later with the same provider/region/settings. The analyzer then compares the latest completed run with the previous one.

```bat
run_windows.bat bán nhà bình chánh
```

Re-analyze at any time:

```bat
python -m ytb_radar --db data\radar.db analyze --top 30
```

Export JSON:

```bat
python -m ytb_radar --db data\radar.db export --top 100 --out reports\latest.json
```

## If YouTube challenges headless mode

Run a small visible-browser test first:

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

For browser selection:

```bat
--browser-channel chrome
--browser-channel msedge
--browser-channel chromium
```

Default `auto` tries installed Chrome, then Edge, then Playwright Chromium.

## Controlled scan from known videos

```bat
python -m ytb_radar --db data\radar.db scan-ids VIDEO_ID_1 VIDEO_ID_2 VIDEO_ID_3 ^
  --provider youtube ^
  --label "competitor-set" ^
  --depth 1 ^
  --recs 20
```

This is useful when search ranking itself would add unwanted bias to the seed set.

## Invidious provider

The older path is still available:

```bat
python -m ytb_radar ping --provider invidious --instance http://127.0.0.1:3000
```

Or let it probe the official public directory:

```bat
python -m ytb_radar ping --provider invidious
```

Inspect public candidates:

```bat
python -m ytb_radar instances
```

For repeatable Invidious research, a pinned self-hosted instance is preferable.

## Reading the report

Example:

```text
TOP RECOMMENDATION LEADERS
1. 18 refs | rank=8.31 | bridge=0.42 | growth=+80.0% | Video X
```

- `18 refs`: 18 crawled source videos pointed to X.
- `rank`: position-weighted recommendation score; appearing near the top contributes more.
- `bridge`: how strongly the video touches graph communities other than its own.
- `growth`: change in recommendation sources versus the previous completed crawl.

Community example:

```text
#1 nhà / bình chánh / bán
#2 đất / huyện / sổ
#3 tphcm / giá / tỷ
```

Expansion example:

```text
#1 nhà/bình chánh/bán -> #3 tphcm/giá/tỷ
cross_edges=23 sources=12 targets=9
```

Treat this as a research lead, not proof of causation. The useful next question is which videos bridge the groups and what audience promise they have in common.

## Test suite

```bat
python -m unittest discover -s tests -v
```

Experiments are recorded under `experiments/`, including failed approaches. The core research question remains:

> Is the recommendation graph stable and structured enough across repeated real observations to reveal useful audience clusters, bridge content, and early expansion signals?
