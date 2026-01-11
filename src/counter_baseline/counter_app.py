# src/counter_baseline/counter_app.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .store_dynamodb import add_delta, get_value


def _normalize_op(op: str) -> str:
    op = (op or "").strip().lower()
    if op in {"inc", "increment", "add", "+"}:
        return "increment"
    if op in {"dec", "decrement", "sub", "-"}:
        return "decrement"
    if op in {"get", "read", "value"}:
        return "get"
    return op


def _delta_for(op: str, amount: int) -> int:
    amt = int(amount) if amount is not None else 1
    if op == "increment":
        return abs(amt)
    if op == "decrement":
        return -abs(amt)
    raise ValueError(f"Operation does not use delta: {op}")


def run_counter(
    *,
    counter_id: str,
    op: str,
    amount: int | None,
    commands: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Baseline con estado explícito en DynamoDB.
    - Modo simple: op/amount
    - Modo batch: commands[] en orden (múltiples operaciones)
    """
    executed: List[Tuple[str, int]] = []

    if commands:
        last_value: int | None = None
        for cmd in commands:
            cmd_op = _normalize_op(cmd.get("op", "get"))
            cmd_amount = cmd.get("amount", 1)

            if cmd_op in {"increment", "decrement"}:
                delta = _delta_for(cmd_op, cmd_amount)
                last_value = add_delta(counter_id, delta)
                executed.append((cmd_op, int(cmd_amount)))
            elif cmd_op == "get":
                last_value = get_value(counter_id)
                executed.append((cmd_op, 0))
            else:
                raise ValueError(f"Unknown op in commands: {cmd_op}")

        return {"value": int(last_value or 0), "executed": executed}

    op = _normalize_op(op)

    if op in {"increment", "decrement"}:
        delta = _delta_for(op, amount if amount is not None else 1)
        value = add_delta(counter_id, delta)
        executed.append((op, int(amount or 1)))
        return {"value": int(value), "executed": executed}

    if op == "get":
        value = get_value(counter_id)
        executed.append((op, 0))
        return {"value": int(value), "executed": executed}

    raise ValueError(f"Unknown op: {op}")

