# Experiment 002 — automatic Invidious instance selection

Date: 2026-08-14

## Problem

The first MVP required users to set `YTB_INVIDIOUS_BASE` before doing anything. That is unnecessary friction for a first test and it incorrectly suggests there is one permanent public Invidious URL.

Public instances also change state. A server can be online while `/api/v1/videos` is disabled, rate-limited, or protected by an anti-bot challenge.

## Hypothesis

The CLI can make instance configuration optional by using the official Invidious instance directory as discovery input and then probing the exact endpoint this project needs.

The selector must not trust uptime alone.

## Implemented selection flow

```text
YTB_INVIDIOUS_BASE / --instance supplied?
        |
   yes  |  no
        |   \
        |    official instances.json
        |             |
        |       HTTPS + not marked down
        |             |
        |       rank candidates
        |             |
        |       probe /api/v1/videos/:id
        |          /      \
        |       fail       pass
        |        |          |
        |      next      select
        |    candidate       |
        +--------------------+
                 |
              crawler
```

A manual instance always wins. This matters because repeated research should ideally stay pinned to the same backend/context.

## Official upstream facts checked before implementation

- Official public-instance directory JSON: `https://api.invidious.io/instances.json`
- Invidious documents `GET /api/v1/videos/:id` and its `recommendedVideos` field.
- Current Invidious configuration has `disable_abusable_api`; when enabled it disables endpoints including `/api/v1/videos`.
- Public instances are expected to deploy rate limiting / challenge-based anti-abuse controls.

These facts mean `api.invidious.io` is useful for discovery, but the actual video endpoint still has to be probed.

## Directory snapshot observation

At implementation time the trusted public clearnet entries in the official directory were advertising `api: false`. This is an important result rather than something to hide: **automatic discovery can find servers, but it cannot manufacture an enabled video API**.

Therefore the expected behavior is:

1. Auto mode tries the official candidates.
2. If one actually exposes `/api/v1/videos`, use it.
3. If none do, fail with a clear explanation and ask for a pinned/self-hosted instance.

The program deliberately does not silently scrape arbitrary untrusted instances outside the official list.

## Offline validation

Added tests for:

- filtering down/non-HTTPS entries from the directory;
- preserving region/API/uptime metadata;
- falling back when candidate #1 fails the video endpoint;
- selecting candidate #2 when its video endpoint succeeds.

Command:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

GitHub Actions is the authoritative run for this repository after the change is pushed.

## User-visible result

Normal first-run path is now:

```bat
set YTB_REGION=VN
python -m ytb_radar ping
```

or simply:

```bat
run_windows.bat minecraft sinh tồn
```

A pinned instance remains available:

```bat
set YTB_INVIDIOUS_BASE=http://127.0.0.1:3000
```

## What this experiment proves

If tests pass, it proves the discovery/fallback control flow is deterministic and the old mandatory configuration step is removed.

It does **not** prove a public instance with `/api/v1/videos` enabled is always available. That is an upstream availability constraint, not something the selector can solve.

## Next experiment

Run `python -m ytb_radar instances` and `python -m ytb_radar ping` from the target Windows/Vietnam network. If no public candidate passes the video probe, the next engineering step is to create a repeatable self-hosted Invidious + Companion setup and keep the radar pinned to it for Experiment 003.
