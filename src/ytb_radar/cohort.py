from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .store import RadarStore


def normalize_video_ids(video_ids: Iterable[str]) -> list[str]:
    """Return deterministic unique YouTube video IDs."""
    return sorted({str(video_id).strip() for video_id in video_ids if str(video_id).strip()})


def cohort_signature(video_ids: Iterable[str]) -> str:
    ids = normalize_video_ids(video_ids)
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return digest[:16]


def cohort_run_label(label: str, video_ids: Iterable[str]) -> str:
    clean = " ".join(str(label or "cohort").split()) or "cohort"
    return f"cohort:{clean}:{cohort_signature(video_ids)}"


def cohort_from_run(store: RadarStore, run_id: int, label: str | None = None) -> dict[str, Any]:
    run = store.get_run(run_id)
    if not run:
        raise ValueError(f"Run #{run_id} does not exist")
    videos = store.fetch_videos_for_run(run_id)
    ids = normalize_video_ids(
        video["video_id"] for video in videos if video.get("role") == "seed"
    )
    if not ids:
        raise ValueError(f"Run #{run_id} has no seed videos")
    cohort_label = label or run.get("query") or f"run-{run_id}"
    return {
        "version": 1,
        "label": cohort_label,
        "signature": cohort_signature(ids),
        "source_run_id": run_id,
        "video_ids": ids,
    }


def write_cohort(payload: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_cohort(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    ids = normalize_video_ids(payload.get("video_ids") or [])
    if not ids:
        raise ValueError("Cohort file contains no video_ids")
    expected = cohort_signature(ids)
    supplied = str(payload.get("signature") or "")
    if supplied and supplied != expected:
        raise ValueError(
            f"Cohort signature mismatch: file={supplied} calculated={expected}"
        )
    return {
        "version": int(payload.get("version") or 1),
        "label": str(payload.get("label") or "cohort"),
        "signature": expected,
        "source_run_id": payload.get("source_run_id"),
        "video_ids": ids,
    }
