# src/counter_baseline/handler.py
from __future__ import annotations

from typing import Any, Dict

from common.api import parse_event, response
from common.ids import get_request_id, get_execution_id, get_counter_id
from common.log import log_metric, log_event
from common.metrics import start_timer, end_timer, metrics_to_dict

from .counter_app import run_counter


def _is_http_event(event: Dict[str, Any]) -> bool:
    return "requestContext" in event or "httpMethod" in event


def lambda_handler(event: Dict[str, Any], context):
    t0 = start_timer()
    execution_id = get_execution_id(event)
    request_id = get_request_id(context)

    try:
        if _is_http_event(event):
            req = parse_event(event)
            counter_id = get_counter_id(req.body, req.query)

            path = (req.path or "").lower()
            if path.endswith("/increment"):
                op = "increment"
            elif path.endswith("/decrement"):
                op = "decrement"
            elif path.endswith("/get") or path.endswith("/value") or path.endswith("/counter"):
                op = "get"
            else:
                op = req.body.get("op", "get")

            amount = req.body.get("amount", 1)
            commands = req.body.get("commands")

            result = run_counter(counter_id=counter_id, op=op, amount=amount, commands=commands)

            m = end_timer(
                t0,
                approach="baseline",
                operation=op,
                counter_id=counter_id,
                request_id=request_id,
                execution_id=execution_id,
                is_replay=False,
            )
            log_metric(metrics_to_dict(m))

            return response(200, {"counter_id": counter_id, **result})

        # Evento directo (invoke)
        counter_id = str(event.get("counter_id", "default"))
        op = str(event.get("op", "get"))
        amount = event.get("amount", 1)
        commands = event.get("commands")

        result = run_counter(counter_id=counter_id, op=op, amount=amount, commands=commands)

        m = end_timer(
            t0,
            approach="baseline",
            operation=op,
            counter_id=counter_id,
            request_id=request_id,
            execution_id=execution_id,
            is_replay=False,
        )
        log_metric(metrics_to_dict(m))

        return {"counter_id": counter_id, **result}

    except Exception as e:
        log_event("counter_baseline_error", {"error": str(e)})
        raise

