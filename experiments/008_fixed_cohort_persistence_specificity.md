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

## Live validation plan

### Step 1 — freeze run #9

```bat
git pull
python -m pip install -e .
python -m ytb_radar --db data\radar.db cohort-save ^
  --run-id 9 ^
  --out cohorts\minecraft_sinh_ton.json ^
  --label "minecraft sinh tồn core"
```

Expected:

```text
cohort saved: ... | seeds=20 | signature=...
```

### Step 2 — create fixed baseline

Run `scan-cohort` once. This creates the first fixed-cohort baseline; growth/persistence history is not yet meaningful.

### Step 3 — repeat the exact cohort

Run `scan-cohort` again later without editing the JSON file or crawl parameters.

Then run `persistence` on the latest fixed run.

### Step 4 — controls

Collect unrelated isolated-watch depth-0 runs with ~20 successful sources, then use `contrast` against the fixed Minecraft run.

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

Exact-video persistence still misses a key phenomenon already visible in runs #8/#9: the same **format family** can persist while individual video IDs rotate. Example families include `100 Days`, `Hardcore`, `Zombie`, `Ocean/Island`, and broader challenge gaming.

After Experiment 008 validates exact fixed-cohort persistence, the next analyzer layer should aggregate semantic/format families across changing exact targets.

## Status

IMPLEMENTED.

UNIT/LIVE VALIDATION PENDING FOR THE NEW v0.3.0 COMMANDS.
