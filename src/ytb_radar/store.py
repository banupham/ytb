from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    query TEXT,
    region TEXT,
    instance TEXT,
    seed_limit INTEGER,
    depth INTEGER,
    recs_per_video INTEGER,
    max_videos INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    author TEXT,
    author_id TEXT,
    view_count INTEGER,
    published INTEGER,
    length_seconds INTEGER,
    live_now INTEGER,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS run_videos (
    run_id INTEGER NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
    video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    depth INTEGER NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (run_id, video_id)
);

CREATE TABLE IF NOT EXISTS recommendation_edges (
    run_id INTEGER NOT NULL REFERENCES crawl_runs(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY (run_id, source_id, target_id)
);

CREATE INDEX IF NOT EXISTS idx_edges_run_target
ON recommendation_edges(run_id, target_id);

CREATE INDEX IF NOT EXISTS idx_edges_run_source
ON recommendation_edges(run_id, source_id);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RadarStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def start_run(
        self,
        *,
        query: str | None,
        region: str,
        instance: str,
        seed_limit: int,
        depth: int,
        recs_per_video: int,
        max_videos: int,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO crawl_runs
                (started_at, query, region, instance, seed_limit, depth, recs_per_video, max_videos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (utc_now(), query, region, instance, seed_limit, depth, recs_per_video, max_videos),
            )
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str = "done", error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE crawl_runs SET finished_at=?, status=?, error=? WHERE id=?",
                (utc_now(), status, error, run_id),
            )

    def upsert_video(self, item: dict[str, Any]) -> None:
        video_id = item.get("videoId")
        if not video_id:
            return
        now = utc_now()
        raw = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        values = (
            str(video_id),
            item.get("title"),
            item.get("author"),
            item.get("authorId"),
            _as_int(item.get("viewCount")),
            _as_int(item.get("published")),
            _as_int(item.get("lengthSeconds")),
            int(bool(item.get("liveNow"))),
            now,
            now,
            raw,
        )
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO videos
                (video_id, title, author, author_id, view_count, published, length_seconds,
                 live_now, first_seen, last_seen, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title=COALESCE(excluded.title, videos.title),
                    author=COALESCE(excluded.author, videos.author),
                    author_id=COALESCE(excluded.author_id, videos.author_id),
                    view_count=COALESCE(excluded.view_count, videos.view_count),
                    published=COALESCE(excluded.published, videos.published),
                    length_seconds=COALESCE(excluded.length_seconds, videos.length_seconds),
                    live_now=excluded.live_now,
                    last_seen=excluded.last_seen,
                    raw_json=excluded.raw_json
                """,
                values,
            )

    def mark_run_video(self, run_id: int, video_id: str, depth: int, role: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO run_videos(run_id, video_id, depth, role)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id, video_id) DO UPDATE SET
                    depth=MIN(run_videos.depth, excluded.depth),
                    role=CASE
                        WHEN run_videos.role='seed' THEN 'seed'
                        ELSE excluded.role
                    END
                """,
                (run_id, video_id, depth, role),
            )

    def add_edge(self, run_id: int, source_id: str, target_id: str, rank: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO recommendation_edges(run_id, source_id, target_id, rank, observed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id, source_id, target_id) DO UPDATE SET
                    rank=MIN(recommendation_edges.rank, excluded.rank),
                    observed_at=excluded.observed_at
                """,
                (run_id, source_id, target_id, rank, utc_now()),
            )

    def latest_run_id(self, status: str = "done") -> int | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM crawl_runs WHERE status=? ORDER BY id DESC LIMIT 1", (status,)
            ).fetchone()
            return int(row["id"]) if row else None

    def previous_run_id(self, run_id: int) -> int | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM crawl_runs
                WHERE status='done' AND id < ?
                ORDER BY id DESC LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            return int(row["id"]) if row else None

    def previous_compatible_run_id(self, run_id: int) -> int | None:
        """Return the newest earlier run with the same research configuration.

        Growth is only meaningful when query, region/provider endpoint, and crawl
        shape match. This prevents e.g. a Minecraft run from being compared to a
        Bình Chánh run or a depth-0 run from being compared to depth-1.
        """
        with self.connect() as conn:
            current = conn.execute(
                "SELECT * FROM crawl_runs WHERE id=?", (run_id,)
            ).fetchone()
            if not current:
                return None
            row = conn.execute(
                """
                SELECT id FROM crawl_runs
                WHERE status='done' AND id < ?
                  AND query IS ?
                  AND region IS ?
                  AND instance IS ?
                  AND seed_limit IS ?
                  AND depth IS ?
                  AND recs_per_video IS ?
                  AND max_videos IS ?
                ORDER BY id DESC LIMIT 1
                """,
                (
                    run_id,
                    current["query"],
                    current["region"],
                    current["instance"],
                    current["seed_limit"],
                    current["depth"],
                    current["recs_per_video"],
                    current["max_videos"],
                ),
            ).fetchone()
            return int(row["id"]) if row else None

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM crawl_runs WHERE id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    def fetch_edges(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT e.source_id, e.target_id, e.rank,
                       s.title AS source_title, s.author AS source_author,
                       t.title AS target_title, t.author AS target_author,
                       t.view_count AS target_view_count
                FROM recommendation_edges e
                JOIN videos s ON s.video_id=e.source_id
                JOIN videos t ON t.video_id=e.target_id
                WHERE e.run_id=?
                ORDER BY e.source_id, e.rank
                """,
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def fetch_videos_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT v.*, rv.depth, rv.role
                FROM run_videos rv
                JOIN videos v ON v.video_id=rv.video_id
                WHERE rv.run_id=?
                """,
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
