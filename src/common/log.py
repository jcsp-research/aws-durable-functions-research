# src/common/log.py
import json
from typing import Dict, Any


def log_metric(metric: Dict[str, Any]) -> None:
    """
    Imprime una sola línea JSON por operación.
    Ideal para CloudWatch Logs → export CSV.
    """
    print(json.dumps({
        "type": "metric",
        **metric
    }))


def log_event(event: str, payload: Dict[str, Any]) -> None:
    """
    Logs de eventos relevantes (errores, recovery, replay).
    """
    print(json.dumps({
        "type": "event",
        "event": event,
        **payload
    }))

