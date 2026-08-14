# Experiment 008 — Fixed cohort, persistence, and niche specificity

Date: 2026-08-14

## Trigger

Runs #8 and #9 established a cleaner isolated-watch baseline for `minecraft sinh tồn`:

```text
run #8: 20 seeds, 20 successful sources, 220 edges
run #9: 20 seeds, 20 successful sources, 231 edges
```

The niche/community structure repeated, but exact search seed overlap was low:

```text
seed overlap = 8
seed Jaccard = 25%
```

Therefore dynamic search is useful for a current topic radar but is a weak basis for strict temporal growth measurement.

## Hypotheses

1. Repeatedly crawling the exact same source video IDs will produce a cleaner measurement of recommendation appearance/disappearance and support change.
2. Targets that recur across several fixed-cohort observations are more useful than one-run recommendation leaders.
3. Targets that are strong in the niche but weak across unrelated control niches are more likely niche-specific; targets strong everywhere are more likely generic/platform-wide noise.

## Implementation — v0.3.0

### Fixed cohort files

A completed run can now be frozen into a deterministic cohort JSON:

```bat
python -m ytb_radar --db data\radar.db cohort-save ^
  --run-id 9 ^
  --out cohorts\minecraft_sinh_ton.json ^
  --label "minecraft sinh tồn core"
```

The cohort contains:

```text
label
source_run_id
sorted unique video_ids
SHA-256-derived cohort signature
```

Repeated scans use:

```bat
python -m ytb_radar --db data\radar.db scan-cohort ^
  --file cohorts\minecraft_sinh_ton.json ^
  --provider youtube ^
  --region VN ^
  --depth 0 ^
  --recs 20 ^
  --delay 1
```

The signature is embedded in the run label. Compatible fixed-cohort runs therefore imply the same explicit seed set, provider identity, region, depth, recommendation limit, and crawl shape.

### Persistence analysis

New command:

```bat
python -m ytb_radar --db data\radar.db persistence ^
  --run-id LAST_FIXED_RUN ^
  --window 5 ^
  --top 30
```

Per exact recommendation target it measures:

- compatible runs present / total;
- presence percentage;
- current normalized source support;
- median support when present;
- median support across all runs including zero;
- maximum support;
- linear support slope in percentage-points per run;
- median recommendation rank;
- transparent persistence score = presence fraction × median positive support.

The output explicitly marks whether the history uses an exact fixed cohort or a dynamic seed set.

### Niche specificity / control contrast

New command:

```bat
python -m ytb_radar --db data\radar.db contrast ^
  --run-id TARGET_RUN ^
  --control-run-ids CONTROL_1 CONTROL_2 ^
  --top 30
```

For targets observed in the niche run it compares:

```text
niche source support
control average support
control maximum support
specificity vs average
specificity vs maximum
number of controls containing the target
```

The conservative sort uses:

```text
niche support - maximum control support
```

This directly attacks generic recommendation noise observed in the earlier experiments.

## Other implementation changes

- `run_windows.bat` now defaults to `depth=0` because direct Watch Next is the clean topic-radar baseline; recursive depth caused topic drift in Experiment 003/004.
- Added deterministic cohort helper tests.
- Added persistence and contrast unit tests.
- Project version bumped to `0.3.0`.

## Live validation

The cohort was frozen from run #9 with:

```text
label='minecraft sinh tồn core'
seeds=20
signature=b7aca788e993ac22
```

### Fixed baseline — run #10

```text
RUN #10 | query='cohort:minecraft sinh tồn core:b7aca788e993ac22' | status=done
videos=206 edges=229 sources=20 communities=12
seeds_found=20 seed_fill=100.0% seed_sources_success=20 seed_sources_failed=0
```

### First exact repeat — run #11

```text
RUN #11 | query='cohort:minecraft sinh tồn core:b7aca788e993ac22' | status=done
videos=204 edges=241 sources=20 communities=11
seeds_found=20 seed_fill=100.0% seed_sources_success=20 seed_sources_failed=0
compared_with_compatible_run=10 seed_overlap=20 seed_jaccard=100.0% comparable_seed_sources=20
```

This is the first strict apples-to-apples recommendation comparison in the project: same 20 seed IDs, same signature, same provider mode, same region, same crawl depth and recommendation count.

## Persistence live result — runs #10 and #11

Command:

```bat
python -m ytb_radar --db data\radar.db persistence ^
  --run-id 11 ^
  --window 5 ^
  --top 30
```

Observed:

```text
runs=[10, 11]
cohort=fixed
common_seeds=20
seed_union=20
source_counts=[20, 20]
```

Top recurring exact targets included:

- `ÔNG SẾP BÉO SỬU NHI SIÊU NỔI LOẠN` — present 2/2, support 25% -> 35%, median 30%;
- Roblox shooting-game challenge — 2/2, 25% -> 30%, median 27.5%;
- Minecraft Zombie 100 Days — 2/2, support 10% -> 20%, median 15%;
- `100 Ngày Ở Vùng Lạnh Nhất Trong Minecraft Hardcore` — 2/2, stable 15%;
- `Tôi Sinh Tồn 7 Ngày Tại Bắc Cực` — 2/2, support 5% -> 20%;
- multiple Minecraft 100 Days / Hardcore / extreme-environment targets recur at roughly 7.5–15% median support.

## Interpretation

### Fixed-cohort mechanism: PASS

The fixed cohort retained exactly the same 20 sources and all source pages succeeded. This removes changing Search results as a confounder.

### Persistence mechanism: PASS technically, but only an initial baseline

With only two fixed observations, every target that appears in both runs is `2/2 = 100%`. Therefore presence percentage is not yet selective enough by itself. Three to five fixed observations will make persistence substantially more discriminating.

### Exact-video persistence is not the same as niche specificity

The strongest persistent exact targets currently include both clearly Minecraft-related targets and unrelated/generic entertainment targets. Therefore persistence alone cannot tell us whether a recommendation is a real Minecraft-specific signal or a platform-wide/common recommendation.

This is an important result rather than a failure: it proves the next required layer is **control contrast**.

### Format-family signal still looks stronger than exact-video identity

Minecraft `100 Days`, `Hardcore`, `Zombie`, `Ocean/Island`, `cold/extreme environment`, and survival variants recur repeatedly across the fixed graph even while exact video IDs rotate. This remains the more promising creator-level signal.

## Next live validation step

Collect two unrelated isolated-watch depth-0 control runs with around 20 successful sources, for example:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --query "nhạc bolero trữ tình" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 0 ^
  --recs 20 ^
  --delay 1
```

and:

```bat
python -m ytb_radar --db data\radar.db scan ^
  --provider youtube ^
  --query "bán nhà bình chánh" ^
  --region VN ^
  --seed-limit 20 ^
  --depth 0 ^
  --recs 20 ^
  --delay 1
```

Then compare the latest Minecraft fixed run against those control run IDs:

```bat
python -m ytb_radar --db data\radar.db contrast ^
  --run-id 11 ^
  --control-run-ids CONTROL_1 CONTROL_2 ^
  --top 30
```

## Status

FIXED-COHORT LIVE VALIDATION: PASS.

PERSISTENCE LIVE VALIDATION: PASS AS INITIAL 2-RUN BASELINE.

NICHE SPECIFICITY / CONTROL CONTRAST: NEXT REQUIRED LIVE TEST.
