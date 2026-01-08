# src/counter/counter_app.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

try:
    from aws_durable_execution_sdk_python import DurableContext  # type: ignore
except ModuleNotFoundError:
    DurableContext = Any  # fallback local

from .steps import init_value, apply_delta, get_value, flaky_step


def _normalize_op(op: str) -> str:
    op = (op or "").strip().lower()
    if op in {"inc", "increment", "add", "+"}:
        return "increment"
    if op in {"dec", "decrement", "sub", "-"}:
        return "decrement"
    if op in {"get", "read", "value"}:
        return "get"
    if op in {"flaky", "fail"}:
        return "flaky"
    return op


def _delta_for(op: str, amount: int) -> int:
    amt = int(amount) if amount is not None else 1
    if op == "increment":
        return abs(amt)
    if op == "decrement":
        return -abs(amt)
    raise ValueError(f"Operation does not use delta: {op}")


# Actor-like workflow: each execution_id identifies a logical actor.
# commands[] acts as a mailbox; steps are message handlers with checkpoint/replay.
def run_counter_workflow(
    context: DurableContext,
    *,
    op: str,
    amount: int | None,
    initial: int = 0,
    commands: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Flujo durable del contador.

    - Si viene `commands`, procesa una lista de operaciones en orden (secuencial).
    - Si no, procesa una sola operación (op/amount).

    IMPORTANTE:
    - Los steps definidos en steps.py esperan siempre (step_context, ...).
    - Por eso aquí llamamos: context.step(fn, *args) en lugar de fn(*args).
    """

    # Estado inicial como step (checkpointed en AWS)
    value = context.step(init_value, initial)

    executed: List[Tuple[str, int]] = []

    # Modo batch: lista de comandos (útil para pruebas de orden + replay)
    if commands:
        for cmd in commands:
            cmd_op = _normalize_op(cmd.get("op", "get"))
            cmd_amount = cmd.get("amount", 1)

            if cmd_op in {"increment", "decrement"}:
                delta = _delta_for(cmd_op, cmd_amount)
                value = context.step(apply_delta, value, delta)
                executed.append((cmd_op, int(cmd_amount)))

            elif cmd_op == "get":
                value = context.step(get_value, value)
                executed.append((cmd_op, 0))

            elif cmd_op == "flaky":
                # Step que puede fallar para observar retries/replay
                context.step(flaky_step, cmd.get("fail_rate", 0.3))
                executed.append((cmd_op, 0))

            else:
                raise ValueError(f"Unknown op in commands: {cmd_op}")

        return {"value": int(value), "executed": executed}

    # Modo simple: una operación
    op = _normalize_op(op)

    if op in {"increment", "decrement"}:
        delta = _delta_for(op, amount if amount is not None else 1)
        value = context.step(apply_delta, value, delta)
        return {"value": int(value), "executed": [(op, int(amount or 1))]}

    if op == "get":
        value = context.step(get_value, value)
        return {"value": int(value), "executed": [(op, 0)]}

    if op == "flaky":
        context.step(flaky_step, 0.3)
        return {"value": int(value), "executed": [(op, 0)]}

    raise ValueError(f"Unknown op: {op}")

