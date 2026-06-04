"""
storage.py — SQLite baza za praćenje viđenih oglasa.
Sprječava duplikate između pokretanja.
"""

import sqlite3
import hashlib
import os
from dataclasses import dataclass
from typing import Optional
from config import DB_PATH


@dataclass
class JobListing:
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    salary: Optional[str] = None
    source: str = ""
    profile: str = ""   # "junior_dev" ili "network_medior"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                hash        TEXT PRIMARY KEY,
                title       TEXT,
                company     TEXT,
                url         TEXT,
                source      TEXT,
                profile     TEXT,
                seen_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def _job_hash(job: JobListing) -> str:
    key = job.url.strip() if job.url else f"{job.title}|{job.company}"
    return hashlib.md5(key.encode()).hexdigest()


def filter_new(jobs: list[JobListing]) -> list[JobListing]:
    """Vrati samo oglase koje još nismo vidjeli, i odmah ih upiši."""
    init_db()
    new_jobs = []
    with sqlite3.connect(DB_PATH) as conn:
        for job in jobs:
            h = _job_hash(job)
            exists = conn.execute(
                "SELECT 1 FROM seen_jobs WHERE hash = ?", (h,)
            ).fetchone()
            if not exists:
                new_jobs.append(job)
                conn.execute(
                    "INSERT INTO seen_jobs (hash, title, company, url, source, profile) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (h, job.title, job.company, job.url, job.source, job.profile)
                )
        conn.commit()
    return new_jobs


def seen_count() -> int:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
