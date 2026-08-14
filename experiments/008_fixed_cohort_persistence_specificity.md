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

Notable targets included:

- `ÔNG SẾP BÉO SỬU NHI SIÊU NỔI LOẠN` — 25% support;
- Roblox shooting-game challenge — 25%;
- hotel-food challenge — 20%;
- `100 Ngày Ở Vùng Lạnh Nhất Trong Minecraft Hardcore` — 15%;
- Minecraft zombie survival — 15%;
- multiple 100 Days / Hardcore / survival targets at 10–15%.

### First exact repeat — run #11

```text
RUN #11 | query='cohort:minecraft sinh tồn core:b7aca788e993ac22' | status=done
videos=204 edges=241 sources=20 communities=11
seeds_found=20 seed_fill=100.0% seed_sources_success=20 seed_sources_failed=0
compared_with_compatible_run=10 seed_overlap=20 seed_jaccard=100.0% comparable_seed_sources=20
```

This is the first strict apples-to-apples recommendation comparison in the project: same 20 seed IDs, same signature, same provider mode, same region, same crawl depth and recommendation count.

Examples from run #11:

- `ÔNG SẾP BÉO SỬU NHI SIÊU NỔI LOẠN` — 25% -> 35% support, +40% raw source count;
- Roblox shooting-game challenge — 25% -> 30%, +20%;
- `100 Ngày Ở Vùng Lạnh Nhất Trong Minecraft Hardcore` — 15% -> 15%, stable;
- `Tôi Sinh Tồn 7 Ngày Tại Bắc Cực` — rose to 20%;
- Minecraft zombie 100-day survival — rose to 20%;
- several Minecraft / 100 Days / Hardcore targets rose into 15–20% support.

Community labels remained overwhelmingly Minecraft / survival / 100 Days / Hardcore in both fixed runs.

## Interpretation of runs #10 and #11

### Fixed-cohort mechanism: PASS

The fixed cohort retained:

```text
20/20 seeds
100% seed overlap
100% successful source pages
same cohort signature
```

This removes the largest confounder found in runs #8/#9: changing YouTube Search results.

### Exact recommendation state still changes meaningfully

Even with identical source pages and isolated contexts, target support moves between runs. Therefore Watch Next is genuinely dynamic over time/context and should be treated as a sampled recommendation state, not a static graph.

### Niche family remains stable

Although exact targets rotate, the dominant content family remains strongly Minecraft / Survival / 100 Days / Hardcore. This reinforces the earlier result that format/theme-family signal is more stable than exact-video identity.

### Generic / adjacent targets persist too

Some non-Minecraft gaming/challenge and generic entertainment targets remain strong across both exact fixed runs. These cannot yet be called audience bridges. The contrast/control experiment is required before promotion to niche-specific signal.

## Next live validation step

Run persistence on the latest fixed run:

```bat
python -m ytb_radar --db data\radar.db persistence ^
  --run-id 11 ^
  --window 5 ^
  --top 30
```

With only two fixed observations available, this output is an initial persistence baseline. Additional fixed scans will make the metric progressively more useful.

After that, collect unrelated control runs and use `contrast` to demote generic targets.

## Success criteria

Fixed-cohort phase is useful if:

- repeated scans retain exactly the same seed set/signature;
- most/all fixed source pages succeed;
- multiple exact targets recur across 2+ observations;
- persistence output distinguishes recurring targets from one-run spikes;
- control contrast demotes exact generic targets that also recur in unrelated niches;
- Minecraft-specific / 100 Days / Hardcore / survival targets retain positive specificity.

No threshold is treated as proof of algorithmic causation or guaranteed future distribution.

## Remaining limitation

Exact-video persistence still misses a key phenomenon already visible in runs #8/#9 and now #10/#11: the same **format family** can persist while individual video IDs rotate. Example families include `100 Days`, `Hardcore`, `Zombie`, `Ocean/Island`, and broader challenge gaming.

After Experiment 008 validates exact fixed-cohort persistence, the next analyzer layer should aggregate semantic/format families across changing exact targets.

## Status

FIXED-COHORT LIVE VALIDATION: PASS.

PERSISTENCE COMMAND: READY FOR LIVE VALIDATION.

CONTROL CONTRAST: NOT YET VALIDATED.
