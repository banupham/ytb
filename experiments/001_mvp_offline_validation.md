# Experiment 001 — MVP offline graph validation

Date: 2026-08-14

## Hypothesis

Before spending requests on real Invidious instances, verify that the collector/storage/analyzer pipeline behaves correctly on a controlled recommendation graph.

## Synthetic graph

Test graph includes multiple source videos pointing at a shared target `X`.

Expected behavior:

- every recommendation becomes a directed edge;
- `X` is ranked as the recommendation hub;
- a later run with one more source pointing to `X` reports growth from 2 to 3 recommenders (+50%);
- the Invidious client reads `recommendedVideos` from `/api/v1/videos/:id`.

## Command

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Result

```text
test_recommendations_reads_documented_field ... ok
test_analyzer_compares_runs_for_expansion ... ok
test_analyzer_finds_recommendation_hub ... ok
test_crawl_builds_recommendation_edges ... ok

Ran 4 tests
OK
```

## Status

PASS.

## What this proves

It proves the internal pipeline and metrics work against deterministic input.

It does **not** prove that a real Invidious instance will return a stable graph or that the resulting communities correspond to meaningful YouTube audiences.

## Next experiment

Run the same Vietnamese niche query several times against one fixed Invidious instance, keeping region, query, seed count, depth and recommendation count constant.

Success criteria:

- enough `recommendedVideos` are returned to form a non-trivial graph;
- major communities recur between runs;
- high-indegree videos are not random on every run;
- cross-community bridge candidates can be manually interpreted as plausible adjacent topics.
