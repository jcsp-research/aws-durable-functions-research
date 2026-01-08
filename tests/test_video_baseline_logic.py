# tests/test_video_baseline_logic.py
from __future__ import annotations

from video_baseline.store_memory import MemoryStore
from video_baseline.pipeline import run_video_baseline


def test_baseline_success():
    store = MemoryStore()
    out = run_video_baseline(
        store,
        job_id="job-ok",
        video_uri="s3://x/in.mp4",
        chunk_s=1,
        fail_rate=0.0,
        max_attempts=2,
        concurrency=4,
    )
    assert out["ok"] is True
    assert out["n_chunks"] == 10
    assert out["final"]["output_uri"].endswith("final.mp4")
    assert store.get_job("job-ok").status == "ASSEMBLED"


def test_baseline_fails_when_always_failing():
    store = MemoryStore()
    out = run_video_baseline(
        store,
        job_id="job-fail",
        video_uri="s3://x/in.mp4",
        chunk_s=1,
        fail_rate=1.0,
        max_attempts=2,
        concurrency=4,
    )
    assert out["ok"] is False
    assert store.get_job("job-fail").status == "FAILED"
