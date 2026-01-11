# src/video_pipeline/pipeline.py
from __future__ import annotations

from typing import Any, Dict, List

try:
    from aws_durable_execution_sdk_python import DurableContext  # type: ignore
except ModuleNotFoundError:
    DurableContext = Any

from .steps import validate_video, chunk_video, encode_chunk, assemble_video


def run_video_pipeline(
    context: DurableContext,
    *,
    video_uri: str,
    chunk_s: int = 1,
    fail_rate: float = 0.0,
) -> Dict[str, Any]:
    """
    Pipeline Phase 2 (durable-ready):
      1) validate
      2) chunk
      3) encode chunks en paralelo (si el runtime lo permite)
      4) assemble

    En local: se ejecuta secuencialmente si no existe map/parallel.
    """
    # 1) validate
    validation = context.step(validate_video, video_uri)
    if not validation.get("ok"):
        return {"ok": False, "error": "validation_failed", "validation": validation}

    metadata = validation["metadata"]

    # 2) chunk
    chunks = context.step(chunk_video, int(metadata["duration_s"]), chunk_s)

    # 3) encode (parallel/map si existe)
    # Si el SDK soporta context.map o context.parallel, lo usamos.
    if hasattr(context, "map"):
        encoded_chunks = context.map(encode_chunk, chunks, fail_rate=fail_rate)  # type: ignore
    elif hasattr(context, "parallel"):
        # ejemplo: construir una lista de tareas y paralelizarlas
        tasks = [lambda c=c: context.step(encode_chunk, c, fail_rate=fail_rate) for c in chunks]
        encoded_chunks = context.parallel(tasks)  # type: ignore
    else:
        # fallback local: secuencial
        encoded_chunks = [context.step(encode_chunk, c, fail_rate=fail_rate) for c in chunks]

    # 4) assemble
    final = context.step(assemble_video, encoded_chunks)

    return {"ok": True, "metadata": metadata, "n_chunks": len(chunks), "final": final}

