# src/counter/local_run.py
from __future__ import annotations

import csv
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .counter_app import run_counter_workflow


class DummyLogger:
    def info(self, msg: str) -> None:
        print(msg)

    def warning(self, msg: str) -> None:
        print(msg)

    def error(self, msg: str) -> None:
        print(msg)


@dataclass
class FakeStepContext:
    logger: Any = DummyLogger()


class FakeContext:
    """
    Contexto local mínimo compatible con:
        context.step(fn, *args, **kwargs)

    NO simula replay real. Solo ejecuta el step inmediatamente.
    """

    def step(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(FakeStepContext(), *args, **kwargs)


def _experiments_paths() -> tuple[str, str]:
    """
    Devuelve (experiments_dir, csv_path) apuntando a:
      <repo>/experiments/phase1_counter_runs.csv
    """
    here = os.path.dirname(__file__)  # .../src/counter
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))  # .../<repo>
    experiments_dir = os.path.join(repo_root, "experiments")
    csv_path = os.path.join(experiments_dir, "phase1_counter_runs.csv")
    return experiments_dir, csv_path


def _ensure_csv(csv_path: str) -> None:
    """
    Cabecera paper-ready (igual estilo que Phase 2):
    run_id,mode,final_value,n_ops,store_ops,retries,time_ms
    """
    if os.path.exists(csv_path):
        return
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "mode", "final_value", "n_ops", "store_ops", "retries", "time_ms"])


def _append_row(csv_path: str, row: list[Any]) -> None:
    with open(csv_path, "a", newline="") as f:
        csv.writer(f).writerow(row)


def main() -> None:
    ctx = FakeContext()
    start = time.perf_counter()

    out = run_counter_workflow(
        ctx,
        op="get",
        amount=1,
        initial=0,
        commands=[
            {"op": "increment", "amount": 1},
            {"op": "increment", "amount": 2},
            {"op": "get"},
            {"op": "decrement", "amount": 1},
        ],
    )

    elapsed_ms = max(1, int((time.perf_counter() - start) * 1000))

    print("\nRESULT:", out)

    # --- Experiments logging ---
    experiments_dir, csv_path = _experiments_paths()
    os.makedirs(experiments_dir, exist_ok=True)
    _ensure_csv(csv_path)

    run_id = str(uuid.uuid4())[:8]
    final_value = int(out.get("value", 0))
    n_ops = len(out.get("executed", []))

    # Durable-local: sin store explícito en esta simulación
    store_ops = 0
    retries = 0

    _append_row(
        csv_path,
        [run_id, "durable-local", final_value, n_ops, store_ops, retries, elapsed_ms],
    )

    print(f"[experiments] wrote: {csv_path}")


if __name__ == "__main__":
    main()

