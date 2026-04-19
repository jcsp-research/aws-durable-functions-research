import os
import time
import json
import math
import uuid
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError


# ============================================================
# Configuración
# ============================================================

FAILURE_TABLE_NAME = os.environ.get("FAILURE_TABLE_NAME", "durable-failure-markers")
JOBS_TABLE_NAME = os.environ.get("TRADITIONAL_JOBS_TABLE_NAME", "traditional-video-jobs")
S3_BUCKET_NAME = os.environ.get("VIDEO_BUCKET_NAME", "durable-video-artifacts")
DEFAULT_CHUNK_DURATION_SECONDS = int(os.environ.get("DEFAULT_CHUNK_DURATION_SECONDS", "10"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))

dynamodb = boto3.resource("dynamodb")

failure_table = dynamodb.Table(FAILURE_TABLE_NAME)
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


# ============================================================
# Métricas / contadores
# ============================================================

IO_COUNTERS = {
    "jobs_table_reads": 0,
    "jobs_table_writes": 0,
    "failure_table_writes": 0,
}


# ============================================================
# Utilidades
# ============================================================

def emit_metric(logger, metric_name: str, data: dict) -> None:
    payload = {"metric_type": metric_name, **data}
    logger.info(f"METRIC {json.dumps(payload, ensure_ascii=False)}")


def to_dynamo_number_dict(data: dict):
    def convert(value):
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, list):
            return [convert(v) for v in value]
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        return value

    return convert(data)


def from_dynamo_number_dict(data: dict):
    def convert(value):
        if isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            return float(value)
        if isinstance(value, list):
            return [convert(v) for v in value]
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        return value

    return convert(data)


def reset_io_counters() -> None:
    IO_COUNTERS["jobs_table_reads"] = 0
    IO_COUNTERS["jobs_table_writes"] = 0
    IO_COUNTERS["failure_table_writes"] = 0


def compute_chunk_count(duration_seconds: int, chunk_duration_seconds: int) -> int:
    return max(1, math.ceil(duration_seconds / chunk_duration_seconds))


def consume_fail_once_marker(marker_id: str) -> bool:
    """
    True -> debe fallar ahora (primer uso)
    False -> ya falló antes, no volver a fallar
    """
    try:
        failure_table.put_item(
            Item={"marker_id": marker_id},
            ConditionExpression="attribute_not_exists(marker_id)"
        )
        IO_COUNTERS["failure_table_writes"] += 1
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "ConditionalCheckFailedException":
            return False

        if error_code in {"ProvisionedThroughputExceededException", "ThrottlingException"}:
            raise RuntimeError(
                f"DynamoDB throttling while consuming failure marker: {error_code}"
            ) from e

        raise


def maybe_fail(*, fail_mode: str, failure_key: str | None, step_name: str, logger) -> None:
    """
    Inyección de fallos controlada.
    fail_mode:
      - none
      - once
      - always
    """
    if fail_mode == "none":
        return

    if fail_mode == "always":
        logger.error(f"Simulated permanent failure in {step_name}")
        raise RuntimeError(f"Simulated permanent failure in {step_name}")

    if fail_mode == "once":
        if not failure_key:
            raise ValueError("fail_mode='once' requires 'failure_key' in the event")

        scoped_key = f"{failure_key}:{step_name}"
        should_fail_now = consume_fail_once_marker(scoped_key)

        if should_fail_now:
            logger.error(f"Simulated transient failure in {step_name}")
            raise RuntimeError(f"Simulated transient failure in {step_name}")
        return

    raise ValueError(f"Unsupported fail_mode: {fail_mode}")


def save_job_state(state: dict) -> None:
    jobs_table.put_item(Item=to_dynamo_number_dict(state))
    IO_COUNTERS["jobs_table_writes"] += 1


def load_job_state(job_id: str) -> dict:
    response = jobs_table.get_item(Key={"job_id": job_id})
    IO_COUNTERS["jobs_table_reads"] += 1
    item = response.get("Item")
    if not item:
        raise KeyError(f"Job state not found for job_id={job_id}")
    return from_dynamo_number_dict(item)


def execute_with_retries(step_name: str, fn, logger, test_case: str, max_retries: int = MAX_RETRIES):
    """
    Retry explícito para baseline tradicional.
    """
    attempt = 0
    while True:
        attempt += 1
        start = time.perf_counter()
        status = "success"

        try:
            result = fn()
            return result

        except Exception:
            status = "error"
            if attempt > max_retries:
                raise
            logger.warning(f"Retrying step={step_name} attempt={attempt}/{max_retries}")

        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            emit_metric(
                logger,
                "step_duration",
                {
                    "test_case": test_case,
                    "step": step_name,
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "status": status,
                    "execution_model": "traditional_sequential_with_explicit_state",
                },
            )


# ============================================================
# Etapas del pipeline tradicional
# ============================================================

def initialize_job(event: dict, logger) -> dict:
    test_case = event.get("test_case", "unknown")
    video = event["video"]
    encoding = event.get("encoding", {})

    job_state = {
        "job_id": event.get("job_id") or str(uuid.uuid4()),
        "video_id": video.get("video_id") or str(uuid.uuid4()),
        "input_uri": video["input_uri"],
        "format": video.get("format", "mp4"),
        "duration_seconds": int(video["duration_seconds"]),
        "resolution": video.get("resolution", "1080p"),
        "codec": encoding.get("codec", "h264"),
        "bitrate_kbps": int(encoding.get("bitrate_kbps", 2000)),
        "chunk_duration_seconds": int(
            encoding.get("chunk_duration_seconds", DEFAULT_CHUNK_DURATION_SECONDS)
        ),
        "status": "initialized",
        "chunks": [],
        "encoded_chunks": [],
        "merged_output_uri": None,
        "version": 0,
        "model": "traditional",
        "test_case": test_case,
    }

    save_job_state(job_state)
    logger.info(f"Initialized traditional video job state job_id={job_state['job_id']}")
    return job_state


def validate_video(state: dict, fail_mode: str, failure_key: str | None, logger) -> dict:
    maybe_fail(
        fail_mode=fail_mode,
        failure_key=failure_key,
        step_name="validate_video",
        logger=logger,
    )

    supported_formats = {"mp4", "mov", "mkv"}
    supported_resolutions = {"720p", "1080p", "1440p", "4k"}

    if state["format"] not in supported_formats:
        return {
            "is_valid": False,
            "error_type": "domain_validation",
            "error_message": f"Unsupported input format: {state['format']}",
            "state": state,
        }

    if state["resolution"] not in supported_resolutions:
        return {
            "is_valid": False,
            "error_type": "domain_validation",
            "error_message": f"Unsupported resolution: {state['resolution']}",
            "state": state,
        }

    if state["duration_seconds"] <= 0:
        return {
            "is_valid": False,
            "error_type": "domain_validation",
            "error_message": "Video duration must be > 0",
            "state": state,
        }

    state["status"] = "validated"
    state["version"] += 1
    save_job_state(state)

    return {"is_valid": True, "state": state}


def split_video(state: dict, fail_mode: str, failure_key: str | None, logger) -> dict:
    maybe_fail(
        fail_mode=fail_mode,
        failure_key=failure_key,
        step_name="split_video",
        logger=logger,
    )

    duration = int(state["duration_seconds"])
    chunk_duration = int(state["chunk_duration_seconds"])
    chunk_count = compute_chunk_count(duration, chunk_duration)

    chunks = []
    for idx in range(chunk_count):
        start_sec = idx * chunk_duration
        end_sec = min(duration, (idx + 1) * chunk_duration)

        chunks.append(
            {
                "chunk_id": f"{state['video_id']}_chunk_{idx:04d}",
                "index": idx,
                "start_second": start_sec,
                "end_second": end_sec,
                "duration_seconds": end_sec - start_sec,
                "source_uri": state["input_uri"],
                "status": "pending",
            }
        )

    state["chunks"] = chunks
    state["status"] = "chunked"
    state["version"] += 1

    save_job_state(state)
    logger.info(f"Generated {chunk_count} chunks for job={state['job_id']}")
    return state


def encode_chunk(job_id: str, chunk: dict, fail_mode: str, failure_key: str | None, logger) -> dict:
    step_name = f"encode_chunk_{chunk['index']}"

    def _run():
        state = load_job_state(job_id)

        maybe_fail(
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name=step_name,
            logger=logger,
        )

        simulated_ms = 100 + (50 * int(chunk["duration_seconds"]))
        time.sleep(simulated_ms / 1000.0)

        encoded = {
            "chunk_id": chunk["chunk_id"],
            "index": chunk["index"],
            "duration_seconds": chunk["duration_seconds"],
            "codec": state["codec"],
            "bitrate_kbps": state["bitrate_kbps"],
            "output_uri": f"s3://{S3_BUCKET_NAME}/encoded/{state['job_id']}/{chunk['chunk_id']}.mp4",
            "status": "encoded",
            "simulated_processing_ms": simulated_ms,
        }

        updated_chunks = []
        for existing in state["chunks"]:
            if existing["chunk_id"] == chunk["chunk_id"]:
                new_chunk = dict(existing)
                new_chunk["status"] = "encoded"
                new_chunk["output_uri"] = encoded["output_uri"]
                updated_chunks.append(new_chunk)
            else:
                updated_chunks.append(existing)

        encoded_chunks = list(state.get("encoded_chunks", []))
        encoded_chunks = [c for c in encoded_chunks if c["chunk_id"] != encoded["chunk_id"]]
        encoded_chunks.append(encoded)

        state["chunks"] = updated_chunks
        state["encoded_chunks"] = sorted(encoded_chunks, key=lambda c: c["index"])
        state["status"] = "encoding"
        state["version"] += 1

        save_job_state(state)
        logger.info(
            f"Encoded chunk index={chunk['index']} for job={state['job_id']} output={encoded['output_uri']}"
        )
        return encoded

    return execute_with_retries(
        step_name=step_name,
        fn=_run,
        logger=logger,
        test_case=load_job_state(job_id).get("test_case", "unknown"),
    )


def merge_video(job_id: str, fail_mode: str, failure_key: str | None, logger) -> dict:
    def _run():
        state = load_job_state(job_id)

        maybe_fail(
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name="merge_video",
            logger=logger,
        )

        time.sleep(0.2)

        ordered_chunks = sorted(state.get("encoded_chunks", []), key=lambda c: c["index"])
        final_uri = f"s3://{S3_BUCKET_NAME}/final/{state['job_id']}/{state['video_id']}_encoded.mp4"

        state["encoded_chunks"] = ordered_chunks
        state["merged_output_uri"] = final_uri
        state["status"] = "merged"
        state["version"] += 1

        save_job_state(state)
        logger.info(f"Merged job={state['job_id']} into {final_uri}")
        return state

    return execute_with_retries(
        step_name="merge_video",
        fn=_run,
        logger=logger,
        test_case=load_job_state(job_id).get("test_case", "unknown"),
    )


def build_response(state: dict, logger) -> dict:
    result = {
        "message": "fase2-video-traditional executed successfully",
        "job_id": state["job_id"],
        "video_id": state["video_id"],
        "status": state["status"],
        "chunk_count": len(state.get("chunks", [])),
        "encoded_chunk_count": len(state.get("encoded_chunks", [])),
        "output_uri": state["merged_output_uri"],
        "version": state["version"],
        "execution_model": "traditional_sequential_with_explicit_state",
        "dynamodb_reads": IO_COUNTERS["jobs_table_reads"],
        "dynamodb_writes": IO_COUNTERS["jobs_table_writes"],
        "failure_marker_writes": IO_COUNTERS["failure_table_writes"],
    }

    logger.info(f"Returning result={result}")
    return result


# ============================================================
# Lambda handler principal
# ============================================================

def lambda_handler(event, context) -> dict:
    """
    Baseline tradicional:
    - sin durable runtime
    - estado persistido manualmente en DynamoDB
    - retries implementados en código
    - mismas etapas funcionales que la versión durable
    - ejecución secuencial: el paralelismo real requeriría
      orquestación adicional manual (p. ej. Step Functions, SQS, fan-out explícito)
    """
    start = time.perf_counter()
    status = "success"
    test_case = event.get("test_case", "unknown")
    reset_io_counters()

    logger = getattr(context, "logger", None)
    if logger is None:
        import logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

    logger.info(f"Received event={event}")

    try:
        failures = event.get("failures", {})

        # 1) Inicialización
        state = execute_with_retries(
            step_name="initialize_job",
            fn=lambda: initialize_job(event, logger),
            logger=logger,
            test_case=test_case,
        )

        job_id = state["job_id"]

        # 2) Validación
        validation_result = execute_with_retries(
            step_name="validate_video",
            fn=lambda: validate_video(
                state=load_job_state(job_id),
                fail_mode=failures.get("validate_video", {}).get("fail_mode", "none"),
                failure_key=failures.get("validate_video", {}).get("failure_key"),
                logger=logger,
            ),
            logger=logger,
            test_case=test_case,
        )

        if not validation_result["is_valid"]:
            emit_metric(
                logger,
                "validation_failure",
                {
                    "test_case": test_case,
                    "error_type": validation_result["error_type"],
                    "error_message": validation_result["error_message"],
                    "execution_model": "traditional_sequential_with_explicit_state",
                },
            )

            invalid_state = validation_result["state"]
            invalid_state["status"] = "validation_failed"
            invalid_state["version"] += 1
            save_job_state(invalid_state)

            return {
                "statusCode": 400,
                "body": {
                    "message": "fase2-video-traditional validation failed",
                    "job_id": invalid_state["job_id"],
                    "video_id": invalid_state["video_id"],
                    "status": "validation_failed",
                    "error_type": validation_result["error_type"],
                    "error_message": validation_result["error_message"],
                    "execution_model": "traditional_sequential_with_explicit_state",
                },
            }

        # 3) Chunking
        state = execute_with_retries(
            step_name="split_video",
            fn=lambda: split_video(
                state=load_job_state(job_id),
                fail_mode=failures.get("split_video", {}).get("fail_mode", "none"),
                failure_key=failures.get("split_video", {}).get("failure_key"),
                logger=logger,
            ),
            logger=logger,
            test_case=test_case,
        )

        # 4) Encoding por chunk (persistencia explícita tras cada uno)
        encoded_chunks = []
        for chunk in state["chunks"]:
            encoded = encode_chunk(
                job_id=job_id,
                chunk=chunk,
                fail_mode=failures.get("encode_chunk", {}).get("fail_mode", "none"),
                failure_key=failures.get("encode_chunk", {}).get("failure_key"),
                logger=logger,
            )
            encoded_chunks.append(encoded)

        emit_metric(
            logger,
            "parallelism_summary",
            {
                "test_case": test_case,
                "requested_parallel_chunks": len(state["chunks"]),
                "executed_chunks": len(encoded_chunks),
                "actual_parallel_chunks": 1,
                "execution_model": "traditional_sequential_with_explicit_state",
            },
        )

        # 5) Merge
        state = merge_video(
            job_id=job_id,
            fail_mode=failures.get("merge_video", {}).get("fail_mode", "none"),
            failure_key=failures.get("merge_video", {}).get("failure_key"),
            logger=logger,
        )

        # 6) Respuesta
        final_state = load_job_state(job_id)
        result = build_response(final_state, logger)

        explicit_state_size_kb = len(json.dumps(final_state, ensure_ascii=False)) / 1024.0
        emit_metric(
            logger,
            "explicit_state_size",
            {
                "test_case": test_case,
                "size_kb": round(explicit_state_size_kb, 3),
                "state_version": final_state.get("version", 0),
                "chunk_count": len(final_state.get("chunks", [])),
                "encoded_chunk_count": len(final_state.get("encoded_chunks", [])),
                "dynamodb_reads": IO_COUNTERS["jobs_table_reads"],
                "dynamodb_writes": IO_COUNTERS["jobs_table_writes"],
                "failure_marker_writes": IO_COUNTERS["failure_table_writes"],
                "execution_model": "traditional_sequential_with_explicit_state",
            },
        )

        return {"statusCode": 200, "body": result}

    except Exception as e:
        status = "error"
        logger.exception("Unhandled error in traditional pipeline")
        return {
            "statusCode": 500,
            "body": {
                "message": "fase2-video-traditional execution failed",
                "test_case": test_case,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_model": "traditional_sequential_with_explicit_state",
                "dynamodb_reads": IO_COUNTERS["jobs_table_reads"],
                "dynamodb_writes": IO_COUNTERS["jobs_table_writes"],
                "failure_marker_writes": IO_COUNTERS["failure_table_writes"],
            },
        }

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            logger,
            "execution_duration",
            {
                "test_case": test_case,
                "duration_ms": duration_ms,
                "status": status,
                "execution_model": "traditional_sequential_with_explicit_state",
                "dynamodb_reads": IO_COUNTERS["jobs_table_reads"],
                "dynamodb_writes": IO_COUNTERS["jobs_table_writes"],
                "failure_marker_writes": IO_COUNTERS["failure_table_writes"],
            },
        )