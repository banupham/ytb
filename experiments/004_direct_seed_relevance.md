# Experiment 004 — Direct-seed recommendation relevance

Date: 2026-08-14

## Why this experiment exists

Experiment 003 proved that the real YouTube browser provider can extract Watch Next recommendations. A depth-1 crawl of `bán nhà bình chánh` produced 267 videos, 500 edges and 45 recommending sources, but the graph quickly accumulated unrelated trending/current-affairs content.

The next question is narrower:

> Are the recommendations directly attached to the original search-result seed videos sufficiently topic-structured to support audience-expansion analysis?

## Main confounder to remove

The Windows wrapper currently uses `--depth 1`. At depth 1, every recommendation discovered from a seed can become a new source page. If one generic/trending video enters the first hop, its own Watch Next list can create a large unrelated branch.

For this experiment we disable recursive expansion:

```text
search query
  -> original seed videos only
  -> Watch Next for each seed
  -> STOP
```

## Command

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --query "bán nhà bình chánh" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 0 ^
  --recs 20 ^
  --delay 1.0
```

## What to inspect

1. Number of actual search seeds returned.
2. Total direct edges from those seeds.
3. Top targets shared by multiple seed videos.
4. Whether shared targets are mostly relevant to real estate / Bình Chánh / adjacent property topics or mostly generic trending content.
5. Whether communities have meaningful topical coherence.
6. Repeat the exact same configuration later to measure persistence; do not compare against a run with different depth/config.

## Initial success criterion

Treat direct-seed graph quality as promising if:

- at least 5 seeds produce recommendations;
- at least 50 direct edges are collected;
- several targets are shared by 2+ seed videos;
- a meaningful fraction of the highest shared targets can be manually interpreted as the same topic or an adjacent audience rather than generic platform-wide recommendations.

No fixed percentage threshold is assumed yet; this run is for measuring the baseline.

## Follow-up controls if noise remains high

- use a fresh isolated browser context per seed to reduce session-history contamination;
- run an unrelated control query and identify targets that occur across both graphs as generic/trending noise;
- down-weight or remove targets that appear broadly across unrelated control topics;
- improve community labels using corpus-relative terms instead of raw frequent title words.

## Status

READY FOR LIVE VALIDATION.
