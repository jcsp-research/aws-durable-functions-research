# src/counter/handler.py
from __future__ import annotations

from typing import Any, Dict

from aws_durable_execution_sdk_python import DurableContext, durable_execution

from common.api import parse_event, response
from common.ids import get_request_id, get_execution_id, get_counter_id
from common.log import log_metric, log_event
from common.metrics import start_timer, end_timer, metrics_to_dict

from .counter_app import run_counter_workflow


def _is_http_event(event: Dict[str, Any]) -> bool:
    return "requestContext" in event or "httpMethod" in event


def _get_lambda_context_id(ctx: DurableContext) -> str:
    # DurableContext guarda el lambda context original en .lambda_context (según SDK)
    base = getattr(ctx, "lambda_context", ctx)
    return get_request_id(base)


@durable_execution
def lambda_handler(event: Dict[str, Any], context: DurableContext):
    """
    Durable handler.
    """
    t0 = start_timer()

    try:
        execution_id = get_execution_id(event)
        request_id = _get_lambda_context_id(context)

        if _is_http_event(event):
            req = parse_event(event)
            counter_id = get_counter_id(req.body, req.query)

            # routing básico por path
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
            initial = req.body.get("initial", 0)
            commands = req.body.get("commands")

            result = run_counter_workflow(
                context,
                op=op,
                amount=amount,
                initial=initial,
                commands=commands,
            )

            m = end_timer(
                t0,
                approach="durable",
                operation=op,
                counter_id=counter_id,
                request_id=request_id,
                execution_id=execution_id,
                is_replay=bool(getattr(context, "is_replay", False)),
            )
            log_metric(metrics_to_dict(m))

            return response(200, {"counter_id": counter_id, **result})

        # Evento “directo” (consola / invoke)
        counter_id = event.get("counter_id", "default")
        op = event.get("op", "get")
        amount = event.get("amount", 1)
        initial = event.get("initial", 0)
        commands = event.get("commands")

        result = run_counter_workflow(
            context,
            op=op,
            amount=amount,
            initial=initial,
            commands=commands,
        )

        m = end_timer(
            t0,
            approach="durable",
            operation=str(op),
            counter_id=str(counter_id),
            request_id=request_id,
            execution_id=execution_id,
            is_replay=bool(getattr(context, "is_replay", False)),
        )
        log_metric(metrics_to_dict(m))

        return {"counter_id": counter_id, **result}

    except Exception as e:
        log_event("counter_error", {"error": str(e)})
        # En durable, un error no manejado marca la ejecución como failed
        raise

