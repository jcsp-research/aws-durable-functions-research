# src/video_baseline/local_run.py
from __future__ import annotations

from .store_memory import MemoryStore
from .pipeline import run_video_baseline
import video_baseline.store_memory as sm
print("STORE_MEMORY_PATH:", sm.__file__)



def main():
    store = MemoryStore()

    out = run_video_baseline(
        store,
        job_id="job-001",
        video_uri="s3://fake-bucket/input/sample.mp4",
        chunk_s=1,
        fail_rate=0.2,      # prueba fallos
        max_attempts=5,     # retries manuales (baseline)
        concurrency=4,
    )

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


if __name__ == "__main__":
    main()

