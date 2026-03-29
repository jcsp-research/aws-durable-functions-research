from aws_durable_execution_sdk_python.context import DurableContext, StepContext, durable_step
from aws_durable_execution_sdk_python.execution import durable_execution


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

    return initial_state


@durable_step
def apply_counter_operation(step_context: StepContext, payload: dict) -> dict:
    """
    Aplica una operación al contador.
    Soporta fail_mode='none' y fail_mode='always'.
    """
    state = payload["state"]
    operation = payload.get("operation", "get_value")
    amount = int(payload.get("amount", 1))
    fail_mode = payload.get("fail_mode", "none")

    step_context.logger.info(
        f"Applying operation={operation}, amount={amount}, fail_mode={fail_mode}, current_state={state}"
    )

    if fail_mode == "always":
        step_context.logger.error("Simulated transient failure in apply_counter_operation")
        raise RuntimeError("Simulated transient failure in apply_counter_operation")

    if operation == "increment":
        state["value"] += amount
        state["version"] += 1

    elif operation == "decrement":
        state["value"] -= amount
        state["version"] += 1

    elif operation == "get_value":
        pass

    else:
        raise ValueError(f"Unsupported operation: {operation}")

    step_context.logger.info(f"Updated state={state}")
    return state


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
    """
    context.logger.info(f"Received event={event}")

    initial_state = event.get("state")
    operation = event.get("operation", "get_value")
    amount = int(event.get("amount", 1))
    fail_mode = event.get("fail_mode", "none")

    state = context.step(initialize_counter(initial_state))

    state = context.step(apply_counter_operation({
        "state": state,
        "operation": operation,
        "amount": amount,
        "fail_mode": fail_mode
    }))

    result = context.step(build_response(state))

    return {
        "statusCode": 200,
        "body": result
    }
