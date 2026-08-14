# Roadmap

## Phase 0 — Validate the signal
- [x] Read Invidious `recommendedVideos`.
- [x] Persist recommendation edges per crawl.
- [x] Rank recommendation hubs.
- [x] Compare repeated crawls.
- [x] Detect topology communities.
- [x] Detect cross-community bridge candidates.
- [x] Export machine-readable JSON.
- [ ] Run real repeated VN niche crawls on one stable/self-hosted instance.
- [ ] Measure graph stability across time.
- [ ] Measure how much region changes the graph.

## Phase 1 — Recommendation radar
- [ ] Scheduled repeated scans.
- [ ] Recommendation velocity time series.
- [ ] New/accelerating/decelerating video alerts.
- [ ] Graph visualization.
- [ ] Store thumbnails and public metadata snapshots.
- [ ] Separate Shorts / long-form / live.

## Phase 2 — Audience expansion research
- [ ] Better semantic labels for graph communities.
- [ ] Score adjacent communities by bridge density and growth.
- [ ] Explain which videos connect two communities.
- [ ] Track creator/channel movement between communities.
- [ ] Generate testable content hypotheses, not guarantees.

## Phase 3 — Creator-side diagnostics
- [ ] Optional authorized YouTube Analytics ingestion.
- [ ] Combine public graph signals with impressions/CTR/retention.
- [ ] Compare channel baseline versus niche baseline.
- [ ] Recommend the next experiment: packaging, hook, topic, or no-change.
