# Experiment 009 — First automatic pipeline result

Date: 2026-08-14

## Automatic run

The first `run_auto.bat` / `auto_radar.py` pipeline completed and produced:

```text
cohort=minecraft sinh tồn core
seeds=20
signature=b7aca788e993ac22
fixed_run=12
controls:
  nhạc bolero trữ tình -> run #13
  bán nhà bình chánh -> run #14
```

This validates the automatic workflow:

```text
fixed cohort scan
-> unrelated controls
-> persistence
-> contrast
-> timestamped JSON/text reports
-> reports/latest_summary.txt
```

## Persistence result

The fixed cohort now has three compatible observations (runs #10, #11, #12).

Several exact targets persisted across all 3/3 runs, including:

- Roblox shooting-game challenge: current support 15%, median 25%, slope -5 pp/run;
- `Tôi Sinh Tồn 7 Ngày Tại Bắc Cực`: current support 20%, median 20%, slope +7.5 pp/run;
- `100 Ngày Ở Vùng Lạnh Nhất Trong Minecraft Hardcore`: current support 10%, median 15%;
- multiple Minecraft 100 Days / Hardcore / zombie / cave / apocalypse targets at roughly 10–15% support.

The Minecraft/survival/100-days family remains persistent at the format/theme level.

## Important methodological finding: exact-ID control contrast is too weak

The first automatic contrast reported `control_max=0%` for nearly every Minecraft target.

This is not strong evidence that every such target is truly niche-specific. Exact video-ID overlap between a Minecraft recommendation graph and unrelated Bolero / real-estate graphs is naturally rare. Therefore:

```text
exact target absent from unrelated controls
!=
proved niche-specific recommendation signal
```

The current exact-ID contrast is useful only for demoting a target when the *same exact video* appears in unrelated controls. It cannot reliably identify semantic/platform noise that rotates through different exact video IDs.

Example: the Roblox shooting-game target persisted 3/3 fixed Minecraft runs and had 15% support in run #12, while the exact target was absent from both unrelated controls. This makes it an interesting Minecraft-adjacent/gaming candidate, but not a proven adjacent audience bridge.

Likewise, generic-looking entertainment/review targets can receive positive exact-ID specificity simply because those exact IDs did not happen to appear in the two control runs.

## Conclusion

### Automatic pipeline: PASS

The one-command workflow successfully executes the full current measurement pipeline and exports the expected report files.

### Fixed-cohort persistence: increasingly useful

Three exact fixed-cohort observations are now available. Repeated Minecraft 100 Days / Hardcore / survival targets are becoming more credible than one-run leaders.

### Exact-ID niche specificity: PARTIAL / insufficient

The control stage needs a semantic or family-level comparison in addition to exact-ID overlap.

## Next technical step

Build a **family/semantic signal layer** that aggregates titles into recurring concept families before persistence/contrast, for example:

```text
100 Days
Hardcore
Zombie / Apocalypse
Ocean / Island
Extreme environment
Minecraft challenge
Roblox / broader gaming challenge
Generic story/review
```

Then compare family support across the Minecraft cohort and controls.

The intended distinction becomes:

```text
Minecraft family support high
control family support low
-> niche-specific family

family support high across many unrelated controls
-> generic/background family
```

This is more robust than requiring the same exact video ID to appear in unrelated niches.

## Status

AUTO PIPELINE LIVE VALIDATION: PASS.

PERSISTENCE LIVE VALIDATION: PASS (3 fixed runs).

EXACT-ID CONTROL CONTRAST: PARTIAL; not sufficient for creator advice.

NEXT: FAMILY/SEMANTIC PERSISTENCE + CONTROL CONTRAST.
