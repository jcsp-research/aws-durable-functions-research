# src/video_pipeline/handler.py
from __future__ import annotations

from typing import Any, Dict

try:
    from aws_durable_execution_sdk_python import DurableContext, durable_execution  # type: ignore
except ModuleNotFoundError:
    DurableContext = Any

    def durable_execution(fn):  # type: ignore
        return fn

from common.ids import get_execution_id, get_request_id
from common.log import log_metric, log_event
from common.metrics import start_timer, end_timer, metrics_to_dict

from .pipeline import run_video_pipeline


@durable_execution
def lambda_handler(event: Dict[str, Any], context: DurableContext):
    t0 = start_timer()
    execution_id = get_execution_id(event)

    # En durable real: el lambda context puede estar en context.lambda_context
    base_ctx = getattr(context, "lambda_context", context)
    request_id = get_request_id(base_ctx)

    try:
        video_uri = event.get("video_uri", "s3://fake-bucket/input/sample.mp4")
        chunk_s = int(event.get("chunk_s", 1))
        fail_rate = float(event.get("fail_rate", 0.0))

        result = run_video_pipeline(context, video_uri=video_uri, chunk_s=chunk_s, fail_rate=fail_rate)

        m = end_timer(
            t0,
            approach="durable",
            operation="video_pipeline",
            counter_id="n/a",
            request_id=request_id,
            execution_id=execution_id,
            is_replay=bool(getattr(context, "is_replay", False)),
        )
        log_metric(metrics_to_dict(m))

        return result

    except Exception as e:
        log_event("video_pipeline_error", {"error": str(e), "execution_id": execution_id})
        raise

