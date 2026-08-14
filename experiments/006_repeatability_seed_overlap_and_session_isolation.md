# Experiment 006 — Repeatability, seed overlap, and session isolation

Date: 2026-08-14

## Trigger

A second depth-0 crawl of the same query and configured crawl shape was run on Windows:

```text
query='minecraft sinh tồn'
seed_limit=20
depth=0
recs=20
region=VN
```

Observed run #7:

```text
videos=110 edges=135 sources=12 communities=10
seeds_found=12 seed_sources_success=12 seed_sources_failed=0
compared_with_compatible_run=6
```

Run #6 had:

```text
videos=120 edges=167 sources=15 communities=11
```

## What repeated successfully

The graph remained strongly Minecraft/survival structured. Community labels again centered on:

- Minecraft;
- survival / sinh tồn;
- 100 days / ngày;
- hardcore;
- island / đảo.

Several meaningful targets persisted across runs, including:

- `Tôi Sinh Tồn 7 Ngày Tại Bắc Cực`;
- `Người Cuối Cùng Rời Khỏi Biệt Thự Sẽ Được Sở Hữu Nó`;
- `100 Ngày Biến Đảo Hoang Thành Căn Cứ Khổng Lồ Trong Minecraft Hardcore`;
- `Tôi đã bẫy Tất Cả Động Vật Ngoài Đời Thực trong Minecraft`;
- `Tôi Đã Sinh Tồn 100 Ngày Ở VÙNG LẠNH NHẤT Trong Minecraft Hardcore`.

This is evidence that the observed recommendation graph contains repeatable niche structure rather than being purely random.

## New confounder #1 — actual seed set changed

Although both runs requested `--seed-limit 20`, run #7 only found 12 search seed videos while run #6 produced 15 recommending sources. The browser provider previously read only the currently rendered first batch of search results. YouTube search lazy-loads more cards, so actual seed composition can vary between runs even when configured `seed_limit` is identical.

This makes raw reference growth misleading. Example:

```text
run #6: 15 source pages
run #7: 12 source pages
```

A target going from 5 refs to 6 refs is shown as +20% by raw counts, but its source support rate changes from 5/15 = 33.3% to 6/12 = 50.0%.

More importantly, if a new seed enters the set and recommends a target, raw refs can rise even if none of the shared source pages changed.

## New confounder #2 — shared temporary YouTube session

Runs #6 and #7 reused one browser context across all seed watch pages. That means opening seed A can modify the temporary YouTube session before seed B is opened. A generic recommendation can then propagate across later source pages because of crawler history rather than because it is independently attached to each source video.

Run #7 exposed this strongly: an unrelated long-form story/review target appeared in 10 of 12 source pages while being absent from the previous run.

That target may represent platform-wide/session-wide recommendation injection rather than a Minecraft audience bridge.

## Changes implemented after run #7

### 1. Search scrolling

The YouTube provider now scrolls the search page and repeatedly collects ordinary `ytd-video-renderer` results until `seed_limit` is reached or the result set stops growing.

Goal: make `--seed-limit 20` actually approach 20 stable seed candidates instead of depending on the first lazy-loaded DOM batch.

### 2. Isolated Watch Next contexts

By default every source video now gets a fresh browser context while reusing the same browser process.

```text
seed A -> fresh context -> Watch Next -> close context
seed B -> fresh context -> Watch Next -> close context
seed C -> fresh context -> Watch Next -> close context
```

This reduces contamination caused by the crawler teaching one temporary YouTube session as it walks through the seed list.

For explicit experiments that want session adaptation, `--shared-session` restores the old behavior.

The provider run identity records `isolated-watch` versus `shared-session`, so the analyzer will not compare these two experiment modes as if they were equivalent.

### 3. Growth on common successful seed sources

A compatible previous run is still selected by query/region/provider/config, but target growth is now measured only on seed source IDs that are present and successful in both runs.

This prevents changing seed composition from creating false recommendation growth.

The report now includes:

```text
seed_fill=...
seed_overlap=...
seed_jaccard=...
comparable_seed_sources=...
```

Recommendation leaders also include normalized source support:

```text
support = recommending source pages / all successful source pages
```

## Interpretation of run #7

**Niche-structure repeatability: promising.**

The community structure remained overwhelmingly Minecraft/survival based across two observations.

**Raw per-target growth from run #6 -> #7: not yet trustworthy.**

The two runs used different actual seed sets and one shared temporary YouTube session.

**Transient generic recommendation noise: confirmed as an important confounder.**

The next experiment should use the new isolated-watch provider and search scrolling. Because isolated-watch has a distinct run identity, its first run establishes a new baseline; the second identical isolated run becomes the first clean persistence/growth comparison.

## Next commands

Update locally:

```bat
git pull
python -m pip install -e .
```

Run the same Minecraft experiment:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --query "minecraft sinh tồn" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 0 ^
  --recs 20 ^
  --delay 1
```

Expected provider line now includes:

```text
isolated-watch
```

Success criteria for the next baseline:

- seed count moves closer to the requested 20;
- all/most seeds produce Watch Next edges;
- Minecraft/survival communities remain coherent;
- generic targets that previously appeared across most source pages are reduced if they were caused by shared-session contamination.

Then repeat the exact same isolated command once more to measure common-seed persistence.
