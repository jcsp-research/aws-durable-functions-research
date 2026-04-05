import os
import time
import boto3
from botocore.exceptions import ClientError

from aws_durable_execution_sdk_python.context import DurableContext, StepContext, durable_step
from aws_durable_execution_sdk_python.execution import durable_execution


# Tabla DynamoDB para controlar fail_once
FAILURE_TABLE_NAME = os.environ.get("FAILURE_TABLE_NAME", "durable-failure-markers")
dynamodb = boto3.resource("dynamodb")
failure_table = dynamodb.Table(FAILURE_TABLE_NAME)


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
def initialize_counter(step_context: StepContext, initial_state: dict | None) -> dict:
    """
    Inicializa el estado del contador.
    Si no viene estado, empieza en 0.
    """
    step_context.logger.info("Initializing counter state")

    if initial_state is None:
        initial_state = {
            "value": 0,
            "version": 0
        }

    return {
        "value": int(initial_state.get("value", 0)),
        "version": int(initial_state.get("version", 0))
    }


@durable_step
def apply_counter_operation(step_context: StepContext, payload: dict) -> dict:
    """
    Aplica una operación al contador.
    Soporta fail_mode='none', fail_mode='always' y fail_mode='once'.
    """
    state = payload["state"]
    operation = payload.get("operation", "get_value")
    amount = int(payload.get("amount", 1))
    fail_mode = payload.get("fail_mode", "none")
    failure_key = payload.get("failure_key")

    step_context.logger.info(
        f"Applying operation={operation}, amount={amount}, fail_mode={fail_mode}, current_state={state}, failure_key={failure_key}"
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


@durable_step
def build_response(step_context: StepContext, state: dict) -> dict:
    """
    Construye la respuesta final.
    """
    result = {
        "message": "fase1-counter-durable executed successfully",
        "counter_value": state["value"],
        "version": state["version"]
    }

    step_context.logger.info(f"Returning result={result}")
    return result


@durable_execution
def lambda_handler(event, context: DurableContext) -> dict:
    """
    Evento esperado:
    {
      "state": {"value": 0, "version": 0},
      "operation": "increment",
      "amount": 1,
      "fail_mode": "none"
    }

    Para fail_once:
    {
      "state": {"value": 0, "version": 0},
      "operation": "increment",
      "amount": 1,
      "fail_mode": "once",
      "failure_key": "phase1-fail-once-test-001"
    }
    """
    context.logger.info(f"Received event={event}")

    initial_state = event.get("state")
    operation = event.get("operation", "get_value")
    amount = int(event.get("amount", 1))
    fail_mode = event.get("fail_mode", "none")
    failure_key = event.get("failure_key")

    state = context.step(initialize_counter(initial_state))

    state = context.step(apply_counter_operation({
        "state": state,
        "operation": operation,
        "amount": amount,
        "fail_mode": fail_mode,
        "failure_key": failure_key,
        "debug_sleep_seconds": event.get("debug_sleep_seconds", 0)
    }))

    result = context.step(build_response(state))

    return {
        "statusCode": 200,
        "body": result
    }