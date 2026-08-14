# YTB Radar

Experimental **YouTube recommendation graph radar**. It observes the real YouTube Watch Next surface, stores directed recommendation edges, and separates four research questions:

1. **Topic radar** — what recommendation neighborhood surrounds a niche now?
2. **Fixed cohort** — what changes when the exact same source videos are measured repeatedly?
3. **Persistence** — which exact recommendation targets recur across compatible measurements?
4. **Niche specificity** — which targets are strong in the niche but weak in unrelated control niches?

The project does **not** claim to reverse-engineer, predict, or guarantee YouTube recommendations. A browser observation means only: **this browser context saw B in Watch Next while viewing A at crawl time**.

## One-command automatic run (Windows)

After a cohort file exists at `cohorts\minecraft_sinh_ton.json`, run:

```bat
run_auto.bat
```

It automatically performs:

```text
fixed cohort scan
    -> control: nhạc bolero trữ tình
    -> control: bán nhà bình chánh
    -> persistence
    -> niche/control contrast
    -> export files
```

The easiest file to read is always:

```text
reports\latest_summary.txt
```

Each run also creates a timestamped folder under `reports\auto\` containing:

```text
summary.txt
manifest.json
fixed_analysis.json
persistence.json
contrast.json
control_*.json
```

Advanced use can override the defaults directly:

```bat
python auto_radar.py --control "nhạc bolero trữ tình" --control "bán nhà bình chánh"
```

## Architecture

```text
RecommendationProvider
        |
        +-- youtube   -> real youtube.com page through Playwright
        |
        +-- invidious -> optional /api/v1/videos/:id provider
        |
        v
      Crawler
        |
        v
      SQLite
        |
        +--> graph analyzer
        +--> persistence analyzer
        +--> niche/control contrast
```

The YouTube browser provider is the default. Each source video is opened in a **fresh isolated browser context** unless `--shared-session` is explicitly requested. This reduces contamination from the crawler's own temporary watch history.

## Requirements

- Windows/Linux/macOS with Python 3.10+.
- Google Chrome or Microsoft Edge recommended.
- Network access to YouTube.

Install on Windows:

```bat
git clone https://github.com/banupham/ytb.git
cd ytb
py -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

Check the browser provider:

```bat
python -m ytb_radar ping
```

## 1. Topic radar

The default Windows wrapper now performs a clean direct-Watch-Next scan:

```bat
run_windows.bat minecraft sinh tồn
```

Equivalent explicit command:

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

`depth=0` is the research default because it answers the narrow question:

```text
search query
   -> search seed videos
   -> direct Watch Next of each seed
   -> STOP
```

Recursive `depth=1+` is still available for graph exploration, but early experiments showed that it can drift quickly into unrelated recommendation branches.

The report includes:

- `refs`: number of source pages pointing to a target;
- `support`: percentage of successful source pages pointing to the target;
- position-weighted `rank` score;
- graph `bridge` score;
- compatible-run growth restricted to common successful search seeds;
- communities and exploratory cross-community edges.

Dynamic-search runs are useful for **current niche structure**, but search seed composition can change heavily between runs. Do not treat their raw growth as a clean time-series measurement.

## 2. Freeze a fixed cohort

After a useful topic run, freeze its exact seed IDs. Example using run #9:

```bat
python -m ytb_radar --db data\radar.db cohort-save ^
  --run-id 9 ^
  --out cohorts\minecraft_sinh_ton.json ^
  --label "minecraft sinh tồn core"
```

The cohort file stores a deterministic signature of the exact seed set.

Repeatedly crawl that exact cohort:

```bat
python -m ytb_radar --db data\radar.db scan-cohort ^
  --file cohorts\minecraft_sinh_ton.json ^
  --provider youtube ^
  --region VN ^
  --depth 0 ^
  --recs 20 ^
  --delay 1
```

`scan-cohort` automatically uses the number of IDs in the cohort as its seed limit and puts the cohort signature into the run label. Therefore only runs with the same explicit seed set and crawl configuration are considered compatible.

This is the preferred mode for measuring recommendation appearance/disappearance and momentum.

## 3. Persistence analysis

After at least two fixed-cohort runs:

```bat
python -m ytb_radar --db data\radar.db persistence ^
  --run-id LAST_RUN_ID ^
  --window 5 ^
  --top 30
```

Persistence reports:

```text
present=4/5
presence=80%
support_now=25%
support_med=20%
slope=+3.5pp/run
rank_med=6
```

Interpretation:

- `presence`: fraction of compatible runs in which the exact target appeared;
- `support_now`: current fraction of successful sources recommending it;
- `support_med`: median support when it was present;
- `slope`: linear support trend in percentage-points per run;
- `rank_med`: typical recommendation position;
- `persistence_score`: transparent combination of recurrence and median support for sorting research leads.

Exact-video persistence is not the same as format/theme persistence. A later semantic layer will aggregate recurring formats such as `100 Days`, `Hardcore`, `Zombie`, or `Ocean survival` even when the exact videos change.

## 4. Niche specificity / generic-noise control

Run unrelated topics with comparable source counts, preferably using the same provider mode. Example controls:

```bat
run_windows.bat bán nhà bình chánh
run_windows.bat nhạc bolero
```

Then contrast a niche run against those control run IDs:

```bat
python -m ytb_radar --db data\radar.db contrast ^
  --run-id TARGET_RUN_ID ^
  --control-run-ids CONTROL_RUN_1 CONTROL_RUN_2 ^
  --top 30
```

The report shows:

```text
niche=35%
control_avg=2%
control_max=5%
specificity=+30pp
```

A target with high niche support and low control support is a stronger niche-specific signal. A target that is strong across unrelated controls is more likely generic/platform-wide noise.

This is a **contrast heuristic**, not causal proof.

## 5. Starting from explicit competitor/source videos

You can still scan explicit IDs directly:

```bat
python -m ytb_radar --db data\radar.db scan-ids VIDEO_ID_1 VIDEO_ID_2 VIDEO_ID_3 ^
  --provider youtube ^
  --label "competitor-set" ^
  --depth 0 ^
  --recs 20
```

For repeated research, prefer saving those IDs as a cohort JSON so the cohort signature is enforced automatically.

## Practical creator workflow

```text
TOPIC RADAR
   -> find core niche / recurring formats / possible adjacent audience
   -> choose representative source videos
   -> freeze fixed cohort
   -> repeat fixed cohort
   -> persistence
   -> unrelated controls
   -> niche specificity
   -> content hypothesis
   -> publish/test
   -> add own video to monitoring
```

The intended creator output is eventually closer to:

```text
CORE: Minecraft Survival
PERSISTENT FORMAT: 100 Days / Hardcore
RECURRING VARIATION: ocean, island, zombie
POSSIBLE ADJACENT AUDIENCE: broader gaming challenge
GENERIC NOISE: targets also strong in unrelated controls

TEST IDEA:
100 Days Hardcore Zombie Survival

Evidence:
- persistent across fixed-cohort scans
- meaningful source support
- low control support
- usually appears high in Watch Next
```

The tool should generate **testable content hypotheses**, not promises of views.

## Browser modes

Default:

```text
isolated-watch
```

Each source gets a fresh temporary browser context. To intentionally study session adaptation instead:

```bat
--shared-session
```

These modes have different provider run identities and are not compared as compatible runs.

If headless YouTube is challenged, use:

```bat
--headed
```

Browser selection:

```bat
--browser-channel chrome
--browser-channel msedge
--browser-channel chromium
```

## Invidious

Invidious remains an optional secondary provider:

```bat
python -m ytb_radar ping --provider invidious --instance http://127.0.0.1:3000
```

Public Invidious instances were not reliable enough in the project tests to remain the primary sensor. A pinned/self-hosted instance is preferable for repeatable Invidious experiments.

## Export and tests

Analyze a crawl:

```bat
python -m ytb_radar --db data\radar.db analyze --run-id RUN_ID --top 30
```

Export JSON:

```bat
python -m ytb_radar --db data\radar.db export --run-id RUN_ID --top 100 --out reports\latest.json
```

Persistence and contrast commands also accept `--json-out`.

Run tests:

```bat
python -m unittest discover -s tests -v
```

Experiments, including failures and confounders, are recorded under `experiments/`.
