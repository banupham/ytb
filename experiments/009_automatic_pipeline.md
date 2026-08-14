# Experiment 009 — Automatic fixed-cohort + controls + export pipeline

Date: 2026-08-14

## Motivation

The manual workflow had become too noisy for day-to-day use. The user should not need to remember a chain of scan, persistence, control, contrast, and export commands.

## Implementation

Added root script:

```text
auto_radar.py
```

and Windows wrapper:

```text
run_auto.bat
```

Default one-command workflow:

```text
fixed cohort scan
    -> unrelated control: nhạc bolero trữ tình
    -> unrelated control: bán nhà bình chánh
    -> persistence analysis
    -> niche/control contrast
    -> JSON + human-readable text export
```

The fixed cohort defaults to:

```text
cohorts/minecraft_sinh_ton.json
```

Each scan gets a fresh `YouTubeBrowserProvider` and the provider itself uses isolated watch contexts for source pages.

## Output

Every invocation creates a timestamped directory:

```text
reports/auto/YYYYMMDD_HHMMSS/
```

with:

```text
summary.txt
manifest.json
fixed_analysis.json
persistence.json
contrast.json
control_*.json
```

A convenience copy is always written to:

```text
reports/latest_summary.txt
```

The human-readable summary includes:

- latest fixed run ID;
- control run IDs;
- top persistent exact targets;
- top niche-specific targets after control subtraction;
- source support and trend fields needed for interpretation.

## Windows usage

After `git pull`, the normal user action is now only:

```bat
run_auto.bat
```

The batch file creates/activates `.venv`, installs the editable project, and runs the automatic pipeline.

## Validation

Added `tests/test_auto_radar.py` for deterministic filename slugging and summary rendering without network access.

Live YouTube validation is pending because it must run from the user's machine/network/browser environment.

## Design limitation

The two default control queries are only a first background estimate. A target absent from those controls is not proven niche-specific globally. Future versions can widen the control pool and add semantic family-level persistence.
