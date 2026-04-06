import os
import time
import json
import math
import uuid
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

from aws_durable_execution_sdk_python.context import DurableContext, StepContext, durable_step
from aws_durable_execution_sdk_python.execution import durable_execution


# ============================================================
# Configuración
# ============================================================

FAILURE_TABLE_NAME = os.environ.get("FAILURE_TABLE_NAME", "durable-failure-markers")
JOBS_TABLE_NAME = os.environ.get("JOBS_TABLE_NAME", "durable-video-jobs")
S3_BUCKET_NAME = os.environ.get("VIDEO_BUCKET_NAME", "durable-video-artifacts")
DEFAULT_CHUNK_DURATION_SECONDS = int(os.environ.get("DEFAULT_CHUNK_DURATION_SECONDS", "10"))

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

failure_table = dynamodb.Table(FAILURE_TABLE_NAME)
jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


# ============================================================
# Utilidades
# ============================================================

def emit_metric(logger, metric_name: str, data: dict) -> None:
    """
    Emite una métrica estructurada en JSON para CloudWatch Logs Insights.
    """
    payload = {"metric_type": metric_name, **data}
    logger.info(f"METRIC {json.dumps(payload, ensure_ascii=False)}")


def consume_fail_once_marker(marker_id: str) -> bool:
    """
    Devuelve True si el marker no existía aún y por tanto debe fallar ahora.
    Devuelve False si ya existía, lo que evita repetir el mismo fallo transitorio.
    """
    try:
        failure_table.put_item(
            Item={"marker_id": marker_id},
            ConditionExpression="attribute_not_exists(marker_id)"
        )
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


def maybe_fail(step_context: StepContext, *, fail_mode: str, failure_key: str | None, step_name: str) -> None:
    """
    Inyección de fallos controlada por step.
    fail_mode:
      - none
      - once
      - always
    """
    if fail_mode == "none":
        return

    if fail_mode == "always":
        step_context.logger.error(f"Simulated permanent failure in {step_name}")
        raise RuntimeError(f"Simulated permanent failure in {step_name}")

    if fail_mode == "once":
        if not failure_key:
            raise ValueError("fail_mode='once' requires 'failure_key' in the event")

        scoped_key = f"{failure_key}:{step_name}"
        should_fail_now = consume_fail_once_marker(scoped_key)

        if should_fail_now:
            step_context.logger.error(f"Simulated transient failure in {step_name}")
            raise RuntimeError(f"Simulated transient failure in {step_name}")

        return

    raise ValueError(f"Unsupported fail_mode: {fail_mode}")


def compute_chunk_count(duration_seconds: int, chunk_duration_seconds: int) -> int:
    return max(1, math.ceil(duration_seconds / chunk_duration_seconds))


def to_dynamo_number_dict(data: dict) -> dict:
    """
    Convierte ints/floats a Decimal para DynamoDB.
    """
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


# ============================================================
# Steps
# ============================================================

@durable_step
def initialize_job(step_context: StepContext, payload: dict) -> dict:
    """
    Inicializa el estado del job de vídeo.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    try:
        step_context.logger.info("Initializing video job state")

        video = payload["video"]
        encoding = payload.get("encoding", {})

        job_state = {
            "job_id": payload.get("job_id") or str(uuid.uuid4()),
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
        }

        jobs_table.put_item(Item=to_dynamo_number_dict(job_state))
        return job_state

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "step_duration",
            {
                "test_case": test_case,
                "step": "initialize_job",
                "duration_ms": duration_ms,
                "status": status,
            },
        )


@durable_step
def validate_video(step_context: StepContext, payload: dict) -> dict:
    """
    Valida metadatos del vídeo.

    Para errores de dominio (formato/resolución/duración inválidos),
    devuelve un resultado estructurado sin lanzar excepción, evitando
    retries innecesarios del runtime durable.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    state = payload["state"]
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    try:
        maybe_fail(
            step_context,
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name="validate_video",
        )

        supported_formats = {"mp4", "mov", "mkv"}
        supported_resolutions = {"720p", "1080p", "1440p", "4k"}

        if state["format"] not in supported_formats:
            status = "domain_error"
            return {
                "is_valid": False,
                "error_type": "domain_validation",
                "error_message": f"Unsupported input format: {state['format']}",
                "state": state,
            }

        if state["resolution"] not in supported_resolutions:
            status = "domain_error"
            return {
                "is_valid": False,
                "error_type": "domain_validation",
                "error_message": f"Unsupported resolution: {state['resolution']}",
                "state": state,
            }

        if state["duration_seconds"] <= 0:
            status = "domain_error"
            return {
                "is_valid": False,
                "error_type": "domain_validation",
                "error_message": "Video duration must be > 0",
                "state": state,
            }

        new_state = dict(state)
        new_state["status"] = "validated"
        new_state["version"] += 1

        jobs_table.put_item(Item=to_dynamo_number_dict(new_state))
        step_context.logger.info(f"Validated job={new_state['job_id']}")

        return {
            "is_valid": True,
            "state": new_state,
        }

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "step_duration",
            {
                "test_case": test_case,
                "step": "validate_video",
                "duration_ms": duration_ms,
                "status": status,
            },
        )


@durable_step
def split_video(step_context: StepContext, payload: dict) -> dict:
    """
    Divide el vídeo en chunks lógicos.
    Nota: aquí no cortamos físicamente el vídeo; construimos metadatos reproducibles.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    state = payload["state"]
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    try:
        maybe_fail(
            step_context,
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name="split_video",
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

        new_state = dict(state)
        new_state["chunks"] = chunks
        new_state["status"] = "chunked"
        new_state["version"] += 1

        jobs_table.put_item(Item=to_dynamo_number_dict(new_state))
        step_context.logger.info(f"Generated {chunk_count} chunks for job={state['job_id']}")
        return new_state

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "step_duration",
            {
                "test_case": test_case,
                "step": "split_video",
                "duration_ms": duration_ms,
                "status": status,
            },
        )


@durable_step
def encode_chunk(step_context: StepContext, payload: dict) -> dict:
    """
    Codifica un chunk lógico.
    En esta fase experimental simulamos la codificación usando tiempo de CPU/espera,
    sin invocar ffmpeg real aún. Esto permite medir control de flujo, retries y overhead.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    state = payload["state"]
    chunk = payload["chunk"]
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    try:
        maybe_fail(
            step_context,
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name=f"encode_chunk_{chunk['index']}",
        )

        # Simulación determinista del coste de encoding:
        # 50 ms por segundo de chunk + latencia base.
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

        step_context.logger.info(
            f"Encoded chunk index={chunk['index']} for job={state['job_id']} output={encoded['output_uri']}"
        )
        return encoded

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "chunk_duration",
            {
                "test_case": test_case,
                "step": "encode_chunk",
                "chunk_index": chunk["index"],
                "duration_ms": duration_ms,
                "status": status,
            },
        )


@durable_step
def merge_video(step_context: StepContext, payload: dict) -> dict:
    """
    Ensambla chunks codificados en una salida final lógica.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    state = payload["state"]
    encoded_chunks = payload["encoded_chunks"]
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    try:
        maybe_fail(
            step_context,
            fail_mode=fail_mode,
            failure_key=failure_key,
            step_name="merge_video",
        )

        time.sleep(0.2)  # pequeña latencia de merge

        ordered_chunks = sorted(encoded_chunks, key=lambda c: c["index"])
        final_uri = f"s3://{S3_BUCKET_NAME}/final/{state['job_id']}/{state['video_id']}_encoded.mp4"

        new_state = dict(state)
        new_state["encoded_chunks"] = ordered_chunks
        new_state["merged_output_uri"] = final_uri
        new_state["status"] = "merged"
        new_state["version"] += 1

        jobs_table.put_item(Item=to_dynamo_number_dict(new_state))
        step_context.logger.info(f"Merged job={state['job_id']} into {final_uri}")
        return new_state

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "step_duration",
            {
                "test_case": test_case,
                "step": "merge_video",
                "duration_ms": duration_ms,
                "status": status,
            },
        )


@durable_step
def build_response(step_context: StepContext, payload: dict) -> dict:
    """
    Construye la respuesta final del job.
    """
    start = time.perf_counter()
    status = "success"
    test_case = payload.get("test_case", "unknown")

    state = payload["state"]

    try:
        result = {
            "message": "fase2-video-durable executed successfully",
            "job_id": state["job_id"],
            "video_id": state["video_id"],
            "status": state["status"],
            "chunk_count": len(state["chunks"]),
            "encoded_chunk_count": len(state["encoded_chunks"]),
            "output_uri": state["merged_output_uri"],
            "version": state["version"],
        }

        step_context.logger.info(f"Returning result={result}")
        return result

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            step_context.logger,
            "step_duration",
            {
                "test_case": test_case,
                "step": "build_response",
                "duration_ms": duration_ms,
                "status": status,
            },
        )


# ============================================================
# Orquestación principal
# ============================================================

@durable_execution
def lambda_handler(event, context: DurableContext) -> dict:
    """
    Evento esperado (ejemplo mínimo):
    {
      "test_case": "video_happy_path_001",
      "video": {
        "video_id": "video-001",
        "input_uri": "s3://my-bucket/input/sample.mp4",
        "format": "mp4",
        "duration_seconds": 95,
        "resolution": "1080p"
      },
      "encoding": {
        "codec": "h264",
        "bitrate_kbps": 2200,
        "chunk_duration_seconds": 10
      },
      "failures": {
        "validate_video": {"fail_mode": "none"},
        "split_video": {"fail_mode": "none"},
        "encode_chunk": {"fail_mode": "none"},
        "merge_video": {"fail_mode": "none"}
      }
    }
    """
    start = time.perf_counter()
    status = "success"

    test_case = event.get("test_case", "unknown")
    context.logger.info(f"Received event={event}")

    try:
        failures = event.get("failures", {})

        state = context.step(
            initialize_job(
                {
                    "job_id": event.get("job_id"),
                    "video": event["video"],
                    "encoding": event.get("encoding", {}),
                    "test_case": test_case,
                }
            )
        )

        validation_result = context.step(
            validate_video(
                {
                    "state": state,
                    "fail_mode": failures.get("validate_video", {}).get("fail_mode", "none"),
                    "failure_key": failures.get("validate_video", {}).get("failure_key"),
                    "test_case": test_case,
                }
            )
        )

        if not validation_result["is_valid"]:
            emit_metric(
                context.logger,
                "validation_failure",
                {
                    "test_case": test_case,
                    "error_type": validation_result["error_type"],
                    "error_message": validation_result["error_message"],
                },
            )

            return {
                "statusCode": 400,
                "body": {
                    "message": "fase2-video-durable validation failed",
                    "job_id": state["job_id"],
                    "video_id": state["video_id"],
                    "status": "validation_failed",
                    "error_type": validation_result["error_type"],
                    "error_message": validation_result["error_message"],
                },
            }

        state = validation_result["state"]

        state = context.step(
            split_video(
                {
                    "state": state,
                    "fail_mode": failures.get("split_video", {}).get("fail_mode", "none"),
                    "failure_key": failures.get("split_video", {}).get("failure_key"),
                    "test_case": test_case,
                }
            )
        )

        # Codificación "paralela" lógica por chunk.
        # Si tu SDK soporta context.parallel / context.map ya estable,
        # esta parte puede migrarse después a paralelismo explícito.
        encoded_chunks = []
        for chunk in state["chunks"]:
            encoded = context.step(
                encode_chunk(
                    {
                        "state": state,
                        "chunk": chunk,
                        "fail_mode": failures.get("encode_chunk", {}).get("fail_mode", "none"),
                        "failure_key": failures.get("encode_chunk", {}).get("failure_key"),
                        "test_case": test_case,
                    }
                )
            )
            encoded_chunks.append(encoded)

        emit_metric(
            context.logger,
            "parallelism_summary",
            {
                "test_case": test_case,
                "requested_parallel_chunks": len(state["chunks"]),
                "executed_chunks": len(encoded_chunks),
            },
        )

        state = context.step(
            merge_video(
                {
                    "state": state,
                    "encoded_chunks": encoded_chunks,
                    "fail_mode": failures.get("merge_video", {}).get("fail_mode", "none"),
                    "failure_key": failures.get("merge_video", {}).get("failure_key"),
                    "test_case": test_case,
                }
            )
        )

        result = context.step(build_response({"state": state, "test_case": test_case}))

        checkpoint_size_kb = len(json.dumps(state, ensure_ascii=False)) / 1024.0

        emit_metric(
            context.logger,
            "checkpoint_size",
            {
                "test_case": test_case,
                "size_kb": round(checkpoint_size_kb, 3),
                "state_version": state.get("version", 0),
                "chunk_count": len(state.get("chunks", [])),
                "encoded_chunk_count": len(state.get("encoded_chunks", [])),
            },
        )

        return {"statusCode": 200, "body": result}

    except Exception:
        status = "error"
        raise

    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        emit_metric(
            context.logger,
            "execution_duration",
            {
                "test_case": test_case,
                "duration_ms": duration_ms,
                "status": status,
            },
        )