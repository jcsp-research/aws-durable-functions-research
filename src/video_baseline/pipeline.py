# src/video_baseline/pipeline.py
from __future__ import annotations

from typing import Dict, Any, List
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from .store_memory import MemoryStore, JobRecord, ChunkRecord


def validate_video_baseline(video_uri: str) -> Dict[str, Any]:
    # Simulación de metadatos
    return {"video_uri": video_uri, "duration_s": 10, "fps": 30, "codec": "h264"}


def chunk_video_baseline(duration_s: int, chunk_s: int) -> List[Dict[str, int]]:
    n = max(1, duration_s // chunk_s)
    return [{"chunk_id": i, "start_s": i * chunk_s, "len_s": chunk_s} for i in range(n)]


def encode_chunk_baseline(chunk: ChunkRecord, *, fail_rate: float) -> str:
    # Simula tiempo de encoding
    time.sleep(0.05)
    if fail_rate > 0 and random.random() < fail_rate:
        raise RuntimeError(f"Simulated encoding failure for chunk {chunk.chunk_id}")
    return f"s3://fake-bucket/encoded/chunk-{chunk.chunk_id:04d}.mp4"


def assemble_baseline(store: MemoryStore, job_id: str) -> Dict[str, Any]:
    chunks = sorted(store.list_chunks(job_id), key=lambda c: c.chunk_id)
    return {
        "output_uri": "s3://fake-bucket/encoded/final.mp4",
        "chunks": [{"chunk_id": c.chunk_id, "encoded_uri": c.encoded_uri} for c in chunks],
    }


def run_video_baseline(
    store: MemoryStore,
    *,
    job_id: str,
    video_uri: str,
    chunk_s: int = 1,
    fail_rate: float = 0.0,
    max_attempts: int = 3,
    concurrency: int = 4,
) -> Dict[str, Any]:
    """
    Baseline tradicional:
    - Estado explícito en store (simula DynamoDB)
    - Retries manuales por chunk
    - Coordinación manual: polling de status de chunks
    """

    # 1) Create job
    store.put_job(JobRecord(job_id=job_id, video_uri=video_uri, chunk_s=chunk_s, status="CREATED"))

    # 2) Validate
    metadata = validate_video_baseline(video_uri)
    store.update_job(job_id, status="VALIDATED", metadata=metadata)

    # 3) Chunk + persist chunks
    chunks = chunk_video_baseline(int(metadata["duration_s"]), chunk_s)
    chunk_records = [
        ChunkRecord(job_id=job_id, chunk_id=c["chunk_id"], start_s=c["start_s"], len_s=c["len_s"])
        for c in chunks
    ]
    store.put_chunks(job_id, chunk_records)
    store.update_job(job_id, status="CHUNKED")

    # 4) Encoding stage (manual coordination)
    store.update_job(job_id, status="ENCODING")

    # Worker que hace retry manual y actualiza el store
    def process_one(chunk_id: int) -> None:
        c = store.get_chunk(job_id, chunk_id)
        while c.attempts < max_attempts and c.status != "DONE":
            try:
                store.update_chunk(job_id, chunk_id, attempts=c.attempts + 1)
                c = store.get_chunk(job_id, chunk_id)
                uri = encode_chunk_baseline(c, fail_rate=fail_rate)
                store.update_chunk(job_id, chunk_id, status="DONE", encoded_uri=uri, error=None)
                return
            except Exception as e:
                store.update_chunk(job_id, chunk_id, status="PENDING", error=str(e))
                c = store.get_chunk(job_id, chunk_id)

        # agotó intentos
        store.update_chunk(job_id, chunk_id, status="FAILED")

    # Ejecutar en paralelo (simula fan-out de Lambdas)
    pending_ids = [c.chunk_id for c in store.list_chunks(job_id)]
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(process_one, cid) for cid in pending_ids]
        for f in as_completed(futures):
            _ = f.result()

    # 5) Polling / check completion
    counts = store.chunk_status_counts(job_id)
    if counts.get("FAILED", 0) > 0:
        store.update_job(job_id, status="FAILED", error=f"{counts['FAILED']} chunks failed")
        return {"ok": False, "job_id": job_id, "metadata": metadata, "counts": counts}

    # 6) Assemble
    final = assemble_baseline(store, job_id)
    store.update_job(job_id, status="ASSEMBLED")

    return {"ok": True, "job_id": job_id, "metadata": metadata, "n_chunks": len(chunks), "final": final}

