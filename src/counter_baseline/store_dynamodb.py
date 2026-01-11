# src/counter_baseline/store_dynamodb.py
from __future__ import annotations

import os
from typing import Dict, Any

import boto3

TABLE_NAME = os.environ.get("COUNTER_TABLE", "CounterTable")
PK_NAME = os.environ.get("COUNTER_PK", "counter_id")

_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(TABLE_NAME)


def get_value(counter_id: str) -> int:
    resp = _table.get_item(Key={PK_NAME: counter_id})
    item = resp.get("Item")
    if not item:
        return 0
    return int(item.get("value", 0))


def set_value(counter_id: str, value: int) -> int:
    _table.put_item(Item={PK_NAME: counter_id, "value": int(value)})
    return int(value)


def add_delta(counter_id: str, delta: int) -> int:
    """
    Incremento/decremento atómico.
    """
    resp = _table.update_item(
        Key={PK_NAME: counter_id},
        UpdateExpression="SET #v = if_not_exists(#v, :zero) + :d",
        ExpressionAttributeNames={"#v": "value"},
        ExpressionAttributeValues={":d": int(delta), ":zero": 0},
        ReturnValues="ALL_NEW",
    )
    attrs = resp.get("Attributes") or {}
    return int(attrs.get("value", 0))

