# src/video_baseline/local_run.py
from __future__ import annotations

import csv
import os
import time
import uuid

import video_baseline.store_memory as sm
from .pipeline import run_video_baseline
from .store_memory import MemoryStore

print("STORE_MEMORY_PATH:", sm.__file__)


def _experiments_paths() -> tuple[str, str]:
    """
    Devuelve (experiments_dir, csv_path) apuntando a:
      <repo>/experiments/phase2_video_runs.csv
    """
    here = os.path.dirname(__file__)  # .../src/video_baseline
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))  # .../<repo>
    experiments_dir = os.path.join(repo_root, "experiments")
    csv_path = os.path.join(experiments_dir, "phase2_video_runs.csv")
    return experiments_dir, csv_path


def _ensure_csv(csv_path: str) -> None:
    if os.path.exists(csv_path):
        return
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "mode", "n_chunks", "store_ops", "retries", "time_ms"])


def _append_row(csv_path: str, row: list[object]) -> None:
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)


def main() -> None:
    store = MemoryStore()

    start = time.perf_counter()

    out = run_video_baseline(
        store,
        job_id="job-001",
        video_uri="s3://fake-bucket/input/sample.mp4",
        chunk_s=1,
        fail_rate=0.2,      # prueba fallos
        max_attempts=5,     # retries manuales (baseline)
        concurrency=4,
    )

    elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))

    print("\nRESULT:", out)

    # Estado final del job
    job = store.get_job("job-001")
    print("\nJOB STATE:", job.status, "error=", job.error)

    # Resumen chunks
    counts = store.chunk_status_counts("job-001")
    print("CHUNK COUNTS:", counts)

    print("STORE CLASS:", type(store))
    print("HAS STATS:", hasattr(store, "stats"))
    print("STATS OBJ:", store.stats)
    print("PUT_JOB FN:", store.put_job)
    print("STORE OPS:", store.stats)

    # --- Experiments logging ---
    experiments_dir, csv_path = _experiments_paths()
    os.makedirs(experiments_dir, exist_ok=True)
    _ensure_csv(csv_path)

    run_id = str(uuid.uuid4())[:8]
    n_chunks = int(out.get("n_chunks", 0))

    # --- 🔒 Guard against invalid runs ---
    if not out.get("ok", False) or n_chunks <= 0:
        print("[experiments] skipped invalid run")
        return

    # Total de operaciones al store (proxy de overhead/coste)
    store_ops = int(sum(store.stats.values())) if hasattr(store, "stats") else 0

    # Proxy simple para "retries": nº de chunks que acabaron FAILED
    retries = int(counts.get("FAILED", 0)) if isinstance(counts, dict) else 0

    _append_row(
        csv_path,
        [run_id, "baseline-local", n_chunks, store_ops, retries, elapsed_ms],
    )


    # Total de operaciones al store (proxy de overhead/coste)
    store_ops = int(sum(store.stats.values())) if hasattr(store, "stats") else 0

    # Proxy simple para "retries": nº de chunks que acabaron FAILED
    retries = int(counts.get("FAILED", 0)) if isinstance(counts, dict) else 0

    _append_row(
        csv_path,
        [run_id, "baseline-local", n_chunks, store_ops, retries, elapsed_ms],
    )

    print(f"[experiments] wrote: {csv_path}")


if __name__ == "__main__":
    main()

