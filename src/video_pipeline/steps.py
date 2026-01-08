# src/video_pipeline/steps.py
from __future__ import annotations

import time
import random
from typing import Any, Dict, List

# Import opcional del SDK durable (como hicimos en counter)
try:
    from aws_durable_execution_sdk_python import durable_step, StepContext  # type: ignore
except ModuleNotFoundError:
    StepContext = Any

    def durable_step(fn):  # type: ignore
        return fn


@durable_step
def validate_video(step_context: StepContext, video_uri: str) -> Dict[str, Any]:
    """
    Simula validación: formato, duración, fps.
    """
    if hasattr(step_context, "logger") and step_context.logger:
        step_context.logger.info(f"[step:validate_video] video_uri={video_uri}")

    # Simulación: metadatos fijos
    metadata = {"video_uri": video_uri, "duration_s": 10, "fps": 30, "codec": "h264"}
    return {"ok": True, "metadata": metadata}


@durable_step
def chunk_video(step_context: StepContext, duration_s: int, chunk_s: int = 1) -> List[Dict[str, Any]]:
    """
    Divide en chunks de tamaño fijo. Devuelve lista de chunks con ids.
    """
    if hasattr(step_context, "logger") and step_context.logger:
        step_context.logger.info(f"[step:chunk_video] duration_s={duration_s} chunk_s={chunk_s}")

    n = max(1, duration_s // chunk_s)
    chunks = [{"chunk_id": i, "start_s": i * chunk_s, "len_s": chunk_s} for i in range(n)]
    return chunks


@durable_step
def encode_chunk(step_context: StepContext, chunk: Dict[str, Any], *, fail_rate: float = 0.0) -> Dict[str, Any]:
    """
    Simula encoding: tarda un poco y puede fallar de forma transitoria.
    """
    cid = chunk["chunk_id"]
    if hasattr(step_context, "logger") and step_context.logger:
        step_context.logger.info(f"[step:encode_chunk] chunk_id={cid} start={chunk['start_s']} len={chunk['len_s']}")

    # Simular tiempo de trabajo proporcional al tamaño
    time.sleep(0.05)

    if fail_rate > 0 and random.random() < fail_rate:
        raise RuntimeError(f"Simulated encoding failure for chunk {cid}")

    # Simula output
    return {"chunk_id": cid, "encoded_uri": f"s3://fake-bucket/encoded/chunk-{cid:04d}.mp4"}


@durable_step
def assemble_video(step_context: StepContext, encoded_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Ensambla la lista de chunks codificados.
    """
    if hasattr(step_context, "logger") and step_context.logger:
        step_context.logger.info(f"[step:assemble_video] n_chunks={len(encoded_chunks)}")

    # Ordenar por chunk_id para garantizar consistencia
    encoded_chunks = sorted(encoded_chunks, key=lambda x: x["chunk_id"])
    output_uri = "s3://fake-bucket/encoded/final.mp4"
    return {"output_uri": output_uri, "chunks": encoded_chunks}

