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

## Live validation — run #5

Observed summary:

```text
RUN #5 | query='bán nhà bình chánh' | status=done
videos=53 edges=81 sources=7 communities=5
compared_with_run=4
```

Top shared recommendation targets were mostly unrelated generic entertainment/audio/story/lifestyle content, for example:

```text
5 refs  | Cô bị mẹ ép bán thân, vô tình leo nhầm xe Tổng tài...
5 refs  | Mở Lòng Vì ai, Mưa Của Trời Mây... Acoustic...
4 refs  | [AUDIO FULL] BỐ MẸ NUÔI BIẾN TÔI THÀNH THIÊN TÀI...
4 refs  | Những Bản Ballad Nhẹ Nhàng Thư Giãn 2026...
4 refs  | Nghịch Lý Cuộc Sống Sau Trục Xuất...
4 refs  | Nữ y tá vào nhầm phòng Tổng tài...
```

Detected communities still contained several property-related labels:

```text
#1 size=17: nhà / bán / bình
#2 size=16: nhà / bán / đẹp
#3 size=7: mới / mặt / nhà
#5 size=6: gần / bình / chánh
```

but one community was visibly contaminated by story content:

```text
#4 size=7: nhà / truyện / tuấn
```

## Interpretation

This run passes the mechanical minimum for graph collection:

- more than 5 sources produced recommendation edges (`sources=7`);
- more than 50 direct edges were collected (`edges=81`);
- several targets were shared by multiple source videos (`3–5 refs`).

However it does **not** pass the semantic usefulness test for audience expansion yet. The highest shared targets are dominated by unrelated generic recommendations, while the useful property/Bình Chánh structure is visible mainly inside the community composition rather than among the top recommendation hubs.

Therefore the important new finding is:

> Removing recursive depth reduced graph size and exposed local property-related structure, but generic/platform-wide recommendation noise is already present in the first hop.

This means depth-1 recursion was not the only source of topic drift.

## Important measurement caveats exposed by run #5

### `sources=7` despite `--seed-limit 20`

The current report only counts source videos that actually contributed at least one stored edge. It does not yet report separately:

- search seeds extracted;
- seed watch pages attempted;
- successful recommendation sources;
- failed/empty sources.

So the current log cannot tell with certainty whether search produced only 7 usable seed videos or whether more seeds were extracted but some failed/returned no stored recommendations. Add explicit crawl counters before interpreting seed coverage.

### `growth` is invalid in this run

Run #5 was compared with run #4 even though run #4 used `depth=1` and run #5 used `depth=0`. Values such as `+400%` are therefore not a valid recommendation-growth measurement.

Future growth comparison must only compare compatible runs: same query, provider, region, depth, seed limit, recommendation limit and preferably the same browser/session policy.

## Next control experiment

The strongest next test is a **negative-control query** collected with the exact same browser configuration, for example an unrelated topic such as `nhạc bolero` or `game minecraft`.

Then compute:

```text
property graph targets
        ∩
unrelated control graph targets
        = generic/platform-wide noise candidates
```

Targets repeatedly shared across unrelated queries should be down-weighted or removed. Targets enriched specifically in the property graph should receive higher audience-relevance weight.

Also test one fresh isolated browser context per seed to distinguish YouTube session-history contamination from genuinely broad logged-out recommendations.

## Status

COLLECTION: PASS.

DIRECT-FIRST-HOP TOPICAL PURITY: FAIL / TOO NOISY.

PROPERTY-RELATED LOCAL STRUCTURE: PRESENT.

NEXT: ADD COVERAGE COUNTERS + MATCHED-RUN COMPARISON + NEGATIVE-CONTROL NOISE FILTER.
