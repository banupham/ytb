# Experiment 007 — First isolated-watch repeat (run #9)

Date: 2026-08-14

## Configuration

Same isolated-watch configuration as run #8:

```text
query='minecraft sinh tồn'
region=VN
seed_limit=20
depth=0
recs=20
isolated-watch=true
```

## Observed run #9

```text
videos=198 edges=231 sources=20 communities=15
seeds_found=20 seed_fill=100.0%
seed_sources_success=20 seed_sources_failed=0
compared_with_compatible_run=8
seed_overlap=8 seed_jaccard=25.0% comparable_seed_sources=8
```

## Main findings

### 1. Niche structure repeated

The community structure again remained overwhelmingly inside Minecraft / survival / 100 Days / Hardcore themes. This is the strongest repeated evidence so far that the observed Watch Next graph contains real topic/audience structure and is not merely random platform-wide content.

Persistent or recurring motifs across isolated runs include:

- Minecraft 100 Days;
- Hardcore survival;
- ocean / island / cold-environment survival;
- zombie / apocalypse Minecraft;
- broader gaming/challenge adjacency such as Roblox.

The useful signal is currently stronger at the **format/theme family** level than at the exact-video level.

### 2. Exact seed composition is highly unstable

Even though both isolated runs reached 20/20 seeds, only 8 seed video IDs were shared.

```text
intersection = 8
union = 32
Jaccard = 8 / 32 = 25%
```

Therefore the same search query does not produce a stable fixed cohort of seed videos. This is now the largest confounder for temporal growth measurement.

Growth values are intentionally computed only from the 8 source videos that were present and successful in both runs. That is safer than raw-count comparison, but the comparable sample is still small.

### 3. Meaning of growth labels

- `+X%` / `-X%`: change only across the common successful seed sources.
- `new`: target was recommended by at least one common source in the current run but by none of those common sources in the previous run.
- `seed-shift`: target exists in the current graph but is absent from both runs when restricted to the common source cohort; it appears because the non-overlapping seed set changed and must not be interpreted as recommendation growth.

### 4. Video-level leaders remain volatile

Run #9's top target was an unrelated long-form story/review video with 35% overall support. This shows that isolated contexts reduce session contamination but do **not** eliminate generic/platform-wide recommendation injection.

The Roblox shooting-game target persisted from run #8 but fell by 50% on the comparable source cohort while still appearing on 30% of all current sources. It remains a plausible adjacent gaming-audience signal, but is not stable enough yet to treat as a recommendation-expansion conclusion.

Several Minecraft-specific targets were more interpretable and recurrent, especially 100 Days, Hardcore, ocean survival, zombie survival, and extreme-environment survival.

### 5. Current expansion-community output is still too fragmented

Most reported cross-community edges are between labels that are semantically almost the same Minecraft niche. Cross-edge counts are also small (mostly 1–2). Therefore the current `AUDIENCE/CLUSTER EXPANSION CANDIDATES` section should not yet be used as creator advice.

## Conclusion

What is now supported by evidence:

1. BrowserProvider can reliably extract direct Watch Next recommendation edges.
2. With isolated contexts and full seed fill, the graph repeatedly forms coherent Minecraft/survival communities.
3. Useful structure is more stable at the topic/format-family level than at the exact recommended-video level.
4. Exact YouTube search seeds are highly volatile, so dynamic-query runs are useful for **current topic radar** but weak for strict temporal growth measurement.
5. Generic recommendation noise remains even after session isolation.

What is **not** supported yet:

- that one top recommendation video should be copied;
- that a high bridge score proves an adjacent audience;
- that a single-run growth percentage means YouTube is globally pushing a target;
- that current community-to-community transitions are strong enough to prescribe the next creator topic.

## Next measurement design

Separate two modes:

### Topic radar mode

Keep dynamic search seeds. Goal: describe the current recommendation neighborhood around a query.

### Fixed-cohort mode

Freeze a known set of seed video IDs and repeatedly crawl the exact same source pages using `scan-ids`. Goal: measure persistence, appearance/disappearance, and recommendation growth without search-result churn.

Only after fixed-cohort persistence is measured should the project promote a signal from `interesting` to `persistent recommendation signal`.
