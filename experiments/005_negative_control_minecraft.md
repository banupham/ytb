# Experiment 005 — Negative control with `minecraft sinh tồn`

Date: 2026-08-14

## Purpose

Experiment 004 showed that a depth-0 crawl for `bán nhà bình chánh` still contained substantial unrelated Watch Next content. We need to distinguish two hypotheses:

1. the YouTube browser session is dominated by generic platform-wide recommendations; or
2. the noise level depends strongly on the niche / seed quality / audience structure.

A clearly different niche is used as a negative control while keeping the crawl shape the same.

## Command

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

## Observed run #6

```text
RUN #6 | query='minecraft sinh tồn' | status=done
videos=120 edges=167 sources=15 communities=11
```

Top shared recommendation targets included:

- `Người Cuối Cùng Rời Khỏi Biệt Thự Sẽ Được Sở Hữu Nó` — 13 refs;
- `Full ( Tập 1 - 30) | Toàn Dân Sinh Tồn Trên Xa Lộ Cực Nóng` — 9 refs;
- `CỐ DÀNH VỊ TRÍ TOP 1 TRONG TEAM NO HOPE !!! | Machine Party` — 8 refs;
- `Tôi Sinh Tồn 7 Ngày Tại Bắc Cực` — 5 refs;
- `TÔI CHƠI THỬ BATTLE ROYALE MỚI MỞ CỦA KINGMC` — 4 refs;
- multiple explicit Minecraft / 100 Days / Hardcore targets with 3–4 refs.

Community labels were much more coherent than the Bình Chánh baseline:

```text
#1 minecraft / ngày / sinh
#2 minecraft / sinh / tồn
#3 ngày / sinh / tồn
#4 minecraft / ngày / hardcore
#5 minecraft / tóm / tắt
#6 minecraft / sinh / lúa
#7 minecraft / sinh / titan
#8 minecraft / ngày / sinh
#9 sinh / tồn / đảo
#10 minecraft / sinh / tồn
```

## Interpretation

This run weakens the hypothesis that the session is simply dominated by the same generic/trending recommendations across all topics.

The Minecraft graph is substantially more topic-coherent than the `bán nhà bình chánh` graph. Most communities remain inside Minecraft / survival / 100 Days / Hardcore territory. Some spillover follows the broader semantic/audience concept of `sinh tồn` (survival), including real-world survival and survival-story content.

That spillover is potentially useful rather than pure noise: it suggests the graph can reveal adjacent audience concepts, but the project must distinguish:

- **core-topic signal** — explicit Minecraft videos;
- **adjacent-audience signal** — survival / challenge / 100 Days formats outside strict Minecraft;
- **generic noise** — unrelated content with no plausible topical or audience bridge.

The contrast with Experiment 004 suggests local real-estate search results may be a harder niche: fewer seeds produced usable recommendation edges and their audiences appear more heterogeneous. This is a property of the observed graph, not proof about all YouTube users.

## Measurement bug exposed

Run #6 printed `compared_with_run=5`, even though run #5 used a different query. Therefore the old growth output is invalid across these runs. The code is being changed so growth is computed only against an earlier run with the same query, region/provider endpoint, seed limit, depth, recommendations per source, and max-videos configuration.

The report is also being changed to print:

- `seeds_found`;
- `seed_sources_success`;
- `seed_sources_failed`.

This will clarify the difference between requested seed limit and the number of source pages that actually produced recommendation edges.

## Current conclusion

**Browser recommendation extraction: PASS.**

**Recommendation graph contains niche structure: PASS for the Minecraft control.**

**Generic-noise-only hypothesis: weakened.**

**Audience-expansion inference: promising but not yet validated.**

## Next falsifiable test

Repeat the exact same Minecraft configuration later. A valid growth/persistence comparison should reuse the same query and crawl parameters. Separately, rerun `bán nhà bình chánh` with the same depth-0 configuration, or improve its seed set with closely related search phrases / explicit video IDs, and compare topical coherence.
