# Experiment 003 — Direct YouTube browser provider

Date: 2026-08-14

## Trigger

A real Windows run using the query `bán nhà bình chánh` successfully installed YTB Radar and reached automatic Invidious selection, but every public candidate failed before the query was executed:

- multiple `/api/v1/videos/:id` requests returned HTTP 403;
- one returned HTTP 401;
- one timed out;
- one Yggdrasil-only hostname could not resolve on the normal network.

This is evidence that public Invidious API availability is not reliable enough to be the only provider for the project.

## Hypothesis

A normal Chromium browser loading youtube.com can provide a usable observation of:

1. YouTube search results for seed discovery;
2. Watch Next recommendation cards for each source video.

If these observations can be collected repeatedly, the existing SQLite + graph analyzer does not need to change.

## Implementation

Version 0.2 adds `YouTubeBrowserProvider` using Playwright.

Default flow:

```text
query
  -> youtube.com/results
  -> search seed videos
  -> youtube.com/watch?v=VIDEO_ID
  -> Watch Next recommendation links
  -> directed recommendation edges
  -> existing SQLite graph/analyzer
```

The CLI defaults to:

```text
--provider youtube
```

The older Invidious provider remains available with:

```text
--provider invidious
```

## Live validation #1 — selector failure

Query: `bán nhà bình chánh`

Observed:

```text
videos=8 edges=0 sources=0 communities=8
```

Search seed extraction succeeded, but all Watch Next lookups failed because the first implementation depended on classic `ytd-compact-video-renderer` selectors.

A headed run visually confirmed that recommendation videos were present, proving selector drift rather than absence of recommendations or an anti-bot page.

## Watch Next v2 fix

The provider now treats normal YouTube watch links (`/watch?v=VIDEO_ID`) inside recommendation/secondary areas as the stable extraction signal rather than depending on one renderer tag. It supports current lockup-style layout plus classic compact renderers and prints DOM diagnostics if extraction fails.

## Live validation #2 — Windows, Watch Next v2

Query: `bán nhà bình chánh`

Observed:

```text
Provider: YouTube browser (headless, channel=auto, region=VN)
crawl complete: run_id=4
RUN #4 | query='bán nhà bình chánh' | status=done
videos=267 edges=500 sources=45 communities=15
```

This satisfies the transport/extraction success criteria by a wide margin:

- search seed discovery works;
- Watch Next extraction works in headless mode;
- 500 directed recommendation edges were observed;
- 45 distinct source watch pages produced recommendations;
- repeated targets occur across many source pages (top target appeared from 23 sources);
- graph/community analysis completes on real observations.

### Important quality finding

The highest-indegree targets include broad current-affairs, entertainment, finance, and other videos not directly related to the search topic. Examples include current news, military/geopolitical coverage, entertainment, and banking/interest-rate content.

This means **BrowserProvider extraction is technically proven, but the raw depth-1 graph must not yet be interpreted as a clean audience-expansion graph for the original topic**.

The current Windows wrapper uses `--depth 1`. That causes recommendation targets from the original real-estate seed pages to be opened as new source pages, and their own recommendations are then added to the same graph. A generic/trending recommendation at depth 1 can therefore pull the crawl into a different topic and amplify it.

A second source of possible noise is the persistent browser session: sequential navigation may allow session-level context to affect later Watch Next observations even without a signed-in account.

### Comparison warning

Run #4 reports `compared_with_run=3`, but the current analyzer simply chooses the previous completed run. If run #3 used different parameters or had a failed/diagnostic graph, `growth=new` is not a valid temporal-growth measurement. Future comparisons must match query/provider/config and require a usable previous graph.

## Result

**EXTRACTION: PASS.**

**RAW GRAPH AS AUDIENCE-EXPANSION EVIDENCE: NOT YET VALIDATED.**

The next experiment must isolate direct recommendations from the original search seeds before recursive expansion is enabled.
