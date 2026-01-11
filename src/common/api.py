# src/common/api.py
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Request:
    method: str
    path: str
    body: Dict[str, Any]
    query: Dict[str, Any]
    headers: Dict[str, Any]


def parse_event(event: Dict[str, Any]) -> Request:
    """
    Soporta:
    - API Gateway HTTP API
    - API Gateway REST API
    - Tests locales
    """
    rc = event.get("requestContext", {})
    http = rc.get("http", {})

    method = http.get("method") or event.get("httpMethod", "GET")
    path = http.get("path") or event.get("path", "/")

    raw_body = event.get("body")
    if raw_body:
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            body = {}
    else:
        body = {}

    query = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}

    return Request(
        method=method,
        path=path,
        body=body,
        query=query,
        headers=headers,
    )


def response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }

