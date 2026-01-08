# src/common/ids.py
import uuid
from typing import Dict, Any


def get_request_id(context) -> str:
    """
    AWS Lambda context request ID
    """
    return getattr(context, "aws_request_id", "unknown")


def get_execution_id(event: Dict[str, Any]) -> str:
    """
    Durable execution name (si existe) o fallback
    """
    return (
        event.get("executionName")
        or event.get("execution_id")
        or str(uuid.uuid4())
    )


def get_counter_id(body: Dict[str, Any], query: Dict[str, Any]) -> str:
    """
    Identidad del contador (actor-like)
    """
    return (
        body.get("counter_id")
        or query.get("counter_id")
        or "default"
    )

