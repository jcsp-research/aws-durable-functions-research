# src/video_baseline/store_memory.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time



@dataclass
class JobRecord:
    job_id: str
    video_uri: str
    chunk_s: int
    status: str = "CREATED"  # CREATED | VALIDATED | CHUNKED | ENCODING | ASSEMBLED | FAILED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ChunkRecord:
    job_id: str
    chunk_id: int
    start_s: int
    len_s: int
    status: str = "PENDING"  # PENDING | DONE | FAILED
    attempts: int = 0
    encoded_uri: Optional[str] = None
    error: Optional[str] = None
    updated_at: float = field(default_factory=time.time)


class MemoryStore:
    """
    Store en memoria que imita tablas:
      - Jobs (por job_id)
      - Chunks (por (job_id, chunk_id))
    Además: contadores de operaciones (proxy de lecturas/escrituras externas).
    """
    def __init__(self):
        self.jobs: Dict[str, JobRecord] = {}
        self.chunks: Dict[str, Dict[int, ChunkRecord]] = {}
        self.stats = {
            "put_job": 0,
            "get_job": 0,
            "update_job": 0,
            "put_chunks": 0,
            "list_chunks": 0,
            "get_chunk": 0,
            "update_chunk": 0,
            "chunk_status_counts": 0,
        }

    # ---- Jobs ----
    def put_job(self, job: JobRecord) -> None:
        self.stats["put_job"] += 1
        self.jobs[job.job_id] = job

    def get_job(self, job_id: str) -> JobRecord:
        self.stats["get_job"] += 1
        return self.jobs[job_id]

    def update_job(self, job_id: str, **fields: Any) -> JobRecord:
        self.stats["update_job"] += 1
        job = self.jobs[job_id]
        for k, v in fields.items():
            setattr(job, k, v)
        job.updated_at = time.time()
        return job

    # ---- Chunks ----
    def put_chunks(self, job_id: str, chunk_records: List[ChunkRecord]) -> None:
        self.stats["put_chunks"] += 1
        self.chunks.setdefault(job_id, {})
        for c in chunk_records:
            self.chunks[job_id][c.chunk_id] = c

    def list_chunks(self, job_id: str) -> List[ChunkRecord]:
        self.stats["list_chunks"] += 1
        return list(self.chunks.get(job_id, {}).values())

    def get_chunk(self, job_id: str, chunk_id: int) -> ChunkRecord:
        self.stats["get_chunk"] += 1
        return self.chunks[job_id][chunk_id]

    def update_chunk(self, job_id: str, chunk_id: int, **fields: Any) -> ChunkRecord:
        self.stats["update_chunk"] += 1
        c = self.chunks[job_id][chunk_id]
        for k, v in fields.items():
            setattr(c, k, v)
        c.updated_at = time.time()
        return c

    def chunk_status_counts(self, job_id: str) -> Dict[str, int]:
        self.stats["chunk_status_counts"] += 1
        counts: Dict[str, int] = {"PENDING": 0, "DONE": 0, "FAILED": 0}
        for c in self.list_chunks(job_id):
            counts[c.status] = counts.get(c.status, 0) + 1
        return counts


