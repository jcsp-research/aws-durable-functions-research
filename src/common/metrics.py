# src/common/metrics.py
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class Metrics:
    approach: str              # durable | baseline
    operation: str             # increment | decrement | get
    counter_id: str
    latency_ms: float
    request_id: str
    execution_id: str
    is_replay: bool = False
    checkpoint_count: int = 0
    checkpoint_bytes: int = 0


def start_timer() -> int:
    return time.perf_counter_ns()


def end_timer(
    start_ns: int,
    *,
    approach: str,
    operation: str,
    counter_id: str,
    request_id: str,
    execution_id: str,
    is_replay: bool = False,
    checkpoint_count: int = 0,
    checkpoint_bytes: int = 0,
) -> Metrics:
    end_ns = time.perf_counter_ns()
    latency_ms = (end_ns - start_ns) / 1_000_000

    return Metrics(
        approach=approach,
        operation=operation,
        counter_id=counter_id,
        latency_ms=latency_ms,
        request_id=request_id,
        execution_id=execution_id,
        is_replay=is_replay,
        checkpoint_count=checkpoint_count,
        checkpoint_bytes=checkpoint_bytes,
    )


def metrics_to_dict(m: Metrics) -> Dict[str, Any]:
    return asdict(m)

