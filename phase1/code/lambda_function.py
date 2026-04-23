import os
import time
import json
import boto3
from botocore.exceptions import ClientError

from aws_durable_execution_sdk_python.context import DurableContext, StepContext, durable_step
from aws_durable_execution_sdk_python.execution import durable_execution


# Tabla DynamoDB para controlar fail_once
FAILURE_TABLE_NAME = os.environ.get("FAILURE_TABLE_NAME", "durable-failure-markers")
dynamodb = boto3.resource("dynamodb")
failure_table = dynamodb.Table(FAILURE_TABLE_NAME)


# ── Detección de replay a nivel módulo ────────────────────────────────────
# Estas variables se inicializan en el cold start del contenedor Lambda y
# se preservan entre invocaciones calientes del mismo contenedor. Permiten
# distinguir la primera invocación en un contenedor (cold) de re-entradas
# (posible replay si el SDK re-invoca tras timeout/error).
_module_load_time = time.time()
_handler_invocation_count = 0


def emit_metric(logger, metric_name: str, data: dict) -> None:
    """
    Emite una métrica estructurada en formato JSON para CloudWatch Logs Insights.
    """
    payload = {
        "metric_type": metric_name,
        **data
    }
    logger.info(f"METRIC {json.dumps(payload, ensure_ascii=False)}")


def consume_fail_once_marker(marker_id: str) -> bool:
    """
    Devuelve True si este marcador no existía aún y, por tanto,
    debemos fallar ahora una sola vez.

    Devuelve False si ya existía y, por tanto,
    no debemos volver a fallar.
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


@durable_step
def initialize_counter(step_context: StepContext, payload: dict) -> dict:
    """
    Inicializa el estado del contador.
    Si no viene estado, empieza en 0.
    """
    start = time.perf_counter()
    status = "success"

    test_case = payload.get("test_case", "unknown")
    initial_state = payload.get("initial_state")

    try:
        step_context.logger.info("Initializing counter state")

        # Replay detection: si este step se ejecuta, NO está cacheado.
        # Cada llamada aquí es una ejecución real, no un replay de checkpoint.
        emit_metric(
            step_context.logger,
            "step_invocation",
            {
                "test_case": test_case,
                "step": "initialize_counter",
                "wall_time": time.time()
            }
        )

        if initial_state is None:
            initial_state = {
                "value": 0,
                "version": 0
            }

        result = {
            "value": int(initial_state.get("value", 0)),
            "version": int(initial_state.get("version", 0))
        }

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
                "step": "initialize_counter",
                "duration_ms": duration_ms,
                "status": status
            }
        )


@durable_step
def apply_counter_operation(step_context: StepContext, payload: dict) -> dict:
    """
    Aplica una operación al contador.
    Soporta fail_mode='none', fail_mode='always' y fail_mode='once'.
    """
    start = time.perf_counter()
    status = "success"

    test_case = payload.get("test_case", "unknown")
    state = payload["state"]
    operation = payload.get("operation", "get_value")
    amount = int(payload.get("amount", 1))
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    try:
        step_context.logger.info(
            f"Applying operation={operation}, amount={amount}, fail_mode={fail_mode}, current_state={state}, failure_key={failure_key}"
        )

        # Replay detection: si este step se ejecuta, NO está cacheado.
        emit_metric(
            step_context.logger,
            "step_invocation",
            {
                "test_case": test_case,
                "step": "apply_counter_operation",
                "operation": operation,
                "fail_mode": fail_mode,
                "wall_time": time.time()
            }
        )

        if payload.get("debug_sleep_seconds", 0):
            time.sleep(int(payload["debug_sleep_seconds"]))

        if fail_mode == "always":
            step_context.logger.error("Simulated permanent failure in apply_counter_operation")
            raise RuntimeError("Simulated permanent failure in apply_counter_operation")

        if fail_mode == "once":
            if not failure_key:
                raise ValueError("fail_mode='once' requires 'failure_key' in the event")

            should_fail_now = consume_fail_once_marker(failure_key)

            if should_fail_now:
                step_context.logger.error("Simulated transient failure on first attempt")
                raise RuntimeError("Simulated transient failure on first attempt")

        # Trabajar sobre una copia del estado
        new_state = {
            "value": int(state["value"]),
            "version": int(state["version"])
        }

        if operation == "increment":
            new_state["value"] += amount
            new_state["version"] += 1

        elif operation == "decrement":
            new_state["value"] -= amount
            new_state["version"] += 1

        elif operation == "get_value":
            pass

        else:
            raise ValueError(f"Unsupported operation: {operation}")

        step_context.logger.info(f"Updated state={new_state}")
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
                "step": "apply_counter_operation",
                "operation": operation,
                "fail_mode": fail_mode,
                "duration_ms": duration_ms,
                "status": status
            }
        )


@durable_step
def build_response(step_context: StepContext, payload: dict) -> dict:
    """
    Construye la respuesta final.
    """
    start = time.perf_counter()
    status = "success"

    test_case = payload.get("test_case", "unknown")
    state = payload["state"]

    try:
        # Replay detection: si este step se ejecuta, NO está cacheado.
        emit_metric(
            step_context.logger,
            "step_invocation",
            {
                "test_case": test_case,
                "step": "build_response",
                "wall_time": time.time()
            }
        )

        result = {
            "message": "fase1-counter-durable executed successfully",
            "counter_value": state["value"],
            "version": state["version"]
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
                "status": status
            }
        )


@durable_execution
def lambda_handler(event, context: DurableContext) -> dict:
    """
    Evento esperado:
    {
      "test_case": "normal_inc_001",
      "state": {"value": 0, "version": 0},
      "operation": "increment",
      "amount": 1,
      "fail_mode": "none"
    }

    Para fail_once:
    {
      "test_case": "fail_once_inc_001",
      "state": {"value": 0, "version": 0},
      "operation": "increment",
      "amount": 1,
      "fail_mode": "once",
      "failure_key": "phase1-fail-once-test-001"
    }
    """
    start = time.perf_counter()
    status = "success"

    # ── Detección de re-invocación (posible replay) ──────────────────────
    # Esta variable global se preserva entre invocaciones calientes del
    # mismo contenedor Lambda. Si invocation_count > 1, este contenedor ha
    # procesado invocaciones previas — posible replay si el SDK re-invoca.
    global _handler_invocation_count
    _handler_invocation_count += 1
    seconds_since_load = round(time.time() - _module_load_time, 3)

    test_case = event.get("test_case", "unknown")
    context.logger.info(f"Received event={event}")

    emit_metric(
        context.logger,
        "invocation_attempt",
        {
            "test_case": test_case,
            "invocation_count": _handler_invocation_count,
            "seconds_since_module_load": seconds_since_load,
            "is_likely_replay": _handler_invocation_count > 1
        }
    )

    try:
        initial_state = event.get("state")
        operation = event.get("operation", "get_value")
        amount = int(event.get("amount", 1))
        fail_mode = event.get("fail_mode", "none")
        failure_key = event.get("failure_key")

        state = context.step(initialize_counter({
            "initial_state": initial_state,
            "test_case": test_case
        }))

        state = context.step(apply_counter_operation({
            "state": state,
            "operation": operation,
            "amount": amount,
            "fail_mode": fail_mode,
            "failure_key": failure_key,
            "debug_sleep_seconds": event.get("debug_sleep_seconds", 0),
            "test_case": test_case
        }))

        result = context.step(build_response({
            "state": state,
            "test_case": test_case
        }))

        # Proxy del tamaño del estado serializado como aproximación
        # del tamaño del checkpoint/state persisted footprint.
        checkpoint_size_kb = len(json.dumps(state, ensure_ascii=False)) / 1024

        emit_metric(
            context.logger,
            "checkpoint_size",
            {
                "test_case": test_case,
                "size_kb": round(checkpoint_size_kb, 3),
                "state_version": state.get("version", 0),
                "counter_value": state.get("value", 0)
            }
        )

        return {
            "statusCode": 200,
            "body": result
        }

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
                "operation": event.get("operation", "get_value"),
                "fail_mode": event.get("fail_mode", "none"),
                "duration_ms": duration_ms,
                "status": status
            }
        )
    
    