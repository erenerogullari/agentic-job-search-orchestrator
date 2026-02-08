"""SQLite-backed storage for deduplicating discovered jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
import sqlite3
import pandas as pd
from typing import List

from src.schema.job import JobListing


@dataclass
class JobDatabase:
    """Simple SQLite wrapper for storing and deduplicating job listings."""

    db_path: str = "data/jobs.db"
    remote: str = ""

    def __post_init__(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                company TEXT,
                date_posted DATE,
                location TEXT,
                remote TEXT,
                status TEXT DEFAULT 'discovered',
                relevance_score REAL
            )
            """
        )
        # Clean exact URL duplicates and ensure a unique index exists.
        self._conn.execute(
            """
            DELETE FROM jobs
            WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM jobs GROUP BY url
            )
            """
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)"
        )
        self._conn.commit()

    def add_jobs(self, jobs: List[JobListing]) -> int:
        """Insert jobs into the DB. Returns number of newly inserted rows."""
        if not jobs:
            return 0

        rows = []
        for job in jobs:
            if isinstance(job.date_posted, datetime):
                date_posted = job.date_posted.date().isoformat()
            elif isinstance(job.date_posted, date):
                date_posted = job.date_posted.isoformat()
            else:
                date_posted = job.date_posted
            rows.append(
                (
                    job.id,
                    job.job_url,
                    job.title,
                    job.company,
                    date_posted,
                    job.location,
                    self.remote,
                )
            )

        before = self._conn.total_changes
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO jobs (
                id, url, title, company, date_posted, location, remote
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.commit()
        return self._conn.total_changes - before

    def get_new_jobs(self, urls: List[str]) -> List[str]:
        """Return only URLs that are not already in the DB."""
        if not urls:
            return []

        placeholders = ",".join("?" for _ in urls)
        query = f"SELECT url FROM jobs WHERE url IN ({placeholders})"
        existing = {row[0] for row in self._conn.execute(query, urls).fetchall()}
        return [url for url in urls if url not in existing]

    def update_scores(self, scores: list[tuple[str, float]]) -> int:
        """Batch-update relevance scores for scored jobs.

        Args:
            scores: list of (job_id, relevance_score) tuples.

        Returns:
            Number of rows updated.
        """
        if not scores:
            return 0

        before = self._conn.total_changes
        self._conn.executemany(
            "UPDATE jobs SET relevance_score = ?, status = 'scored' WHERE id = ?",
            [(score, job_id) for job_id, score in scores],
        )
        self._conn.commit()
        return self._conn.total_changes - before

    def db_to_df(self) -> pd.DataFrame:
        """Return the DB as a pandas DataFrame."""
        df = pd.read_sql_query("SELECT * FROM jobs", self._conn)
        df.drop(columns=["id"], inplace=True)
        return df