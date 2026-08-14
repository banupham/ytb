# YTB Radar

Experimental **YouTube recommendation graph radar** built around observations returned by an Invidious instance.

The project does **not** claim to reverse-engineer or guarantee YouTube recommendations. Its purpose is to collect repeated recommendation observations, build a graph, measure expansion, and turn those observations into testable hypotheses for creators.

## What the MVP can do

- Search a niche through Invidious and use the results as seed videos.
- Start from explicit YouTube video IDs.
- Fetch `GET /api/v1/videos/:id` and read the documented `recommendedVideos` field.
- Store every crawl in SQLite so later runs can be compared.
- Build a directed recommendation graph: `source video -> recommended video`.
- Rank videos by:
  - how many different source videos recommend them;
  - position-weighted recommendation score;
  - change versus the previous crawl.
- Detect graph communities from topology.
- Find bridge candidates between communities.
- List cross-community paths as **expansion opportunities**.
- Export a JSON report for a future dashboard/model.
- Auto-discover public Invidious instances from the official instance directory and probe fallback candidates.
- Still allow a specific instance to be pinned for repeatable research.

## Important interpretation rule

A recommendation edge means:

> At crawl time, the configured Invidious/YouTube context returned target video **B** in the recommendations for source video **A**.

It does **not** mean every YouTube user sees B, and it does not prove why YouTube recommended B. Repeated observations are useful as signals, not as a secret algorithm rule.

## Requirements

- Python 3.10+
- Network access to an Invidious instance.

Public Invidious instances can be unstable, rate-limited, protected by anti-bot systems, or have `/api/v1/videos` disabled. Auto mode handles discovery/fallback, but self-hosting or pinning a known-working instance is preferred for repeatable research.

Install:

```bash
git clone https://github.com/banupham/ytb.git
cd ytb
py -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

## Instance selection

The normal case no longer requires `YTB_INVIDIOUS_BASE`.

```bat
set YTB_REGION=VN
python -m ytb_radar ping
```

When no instance is configured, `ytb-radar`:

1. reads `https://api.invidious.io/instances.json`;
2. keeps healthy HTTPS candidates;
3. prioritizes instances advertising API support and better uptime;
4. probes the actual `/api/v1/videos/:id` endpoint;
5. falls back to the next candidate if a server is blocked, disabled or invalid.

Inspect candidates:

```bat
python -m ytb_radar instances
```

For controlled/repeatable research, or if no public instance currently exposes the video API, pin a known-working/self-hosted instance:

```bat
set YTB_INVIDIOUS_BASE=http://127.0.0.1:3000
set YTB_REGION=VN
python -m ytb_radar ping
```

`--instance URL` overrides automatic selection for a single command.

## First real experiment

Scan a Vietnamese niche:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --query "minecraft sinh tồn" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 1 ^
  --recs 20 ^
  --max-videos 200 ^
  --delay 0.5
```

The scan immediately prints an analysis.

Run the same scan again later:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --query "minecraft sinh tồn" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 1 ^
  --recs 20 ^
  --max-videos 200 ^
  --delay 0.5
```

Now the analyzer can compare the latest run to the preceding completed run.

Re-analyze:

```bat
python -m ytb_radar --db data\radar.db analyze --top 30
```

Export JSON:

```bat
python -m ytb_radar --db data\radar.db export --top 100 --out reports\latest.json
```

You can also start from known videos:

```bat
python -m ytb_radar --db data\radar.db scan-ids VIDEO_ID_1 VIDEO_ID_2 VIDEO_ID_3 ^
  --label "competitor-set" ^
  --depth 1 ^
  --recs 20
```

Quick Windows wrapper; no instance setup is required unless auto mode cannot find a usable public API:

```bat
run_windows.bat minecraft sinh tồn
```

## What the report means

Example idea:

```text
TOP RECOMMENDATION LEADERS
 1.  18 refs | rank=8.31 | bridge=0.42 | growth= +80.0% | Video X
```

Interpretation:

- `18 refs`: 18 crawled source videos pointed to X.
- `rank`: higher when X appears frequently and near the top.
- `bridge`: fraction of X's graph neighbors that belong to another detected community.
- `growth`: change in unique recommending sources versus the previous completed crawl.

Community output:

```text
#1 size=84: minecraft / hardcore / survival
#2 size=51: horror / mod / monster
```

Expansion output:

```text
#1 minecraft/hardcore/survival -> #2 horror/mod/monster
cross_edges=23 sources=12 targets=9
```

This is a **research lead**: inspect bridge videos connecting those groups and test whether a creator can make content that naturally serves both viewer interests.

## Architecture

```text
Official Invidious directory
        |
        v
 instance discovery + probe/fallback
        |
        v
    Invidious
       |
       +-- search --------------------+
       |                              |
       +-- /api/v1/videos/:id         |
                 |                    |
                 +-- recommendedVideos|
                                      v
                             RecommendationCrawler
                                      |
                                      v
                                   SQLite
                                      |
                                      v
                             Graph Analyzer
                     +----------------+----------------+
                     |                |                |
                  leaders         communities       bridges
                     |                |                |
                     +----------------+----------------+
                                      |
                                      v
                           expansion opportunities
```

## Test suite

```bat
python -m unittest discover -s tests -v
```

The offline suite covers the documented recommendation field, instance-directory filtering, instance fallback, edge collection, hub detection, and run-to-run expansion measurement. See `experiments/001_mvp_offline_validation.md` and `experiments/002_auto_instance_selection.md`.

## Current boundary

This MVP deliberately does **not** yet ingest private YouTube Studio metrics such as impressions, CTR, or audience retention. That will be a separate data source. The current experiment asks a narrower question first:

> Is the public recommendation graph stable and structured enough to reveal hubs, communities, bridges, and expanding videos?

If the answer is yes on real repeated crawls, then the next phase is worth building.
