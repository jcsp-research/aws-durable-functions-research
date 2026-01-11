# src/video_pipeline/local_run.py
from __future__ import annotations

import csv
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .pipeline import run_video_pipeline


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
    Contexto local mínimo para simular:
      - context.step(fn, *args, **kwargs)
      - retries (durable-like) en steps que fallen

    Además, registra métricas locales:
      - retry_count: nº total de reintentos (fallos) antes de un éxito
      - failed_steps: nº de steps que terminaron fallando (sin éxito)
    """

    def __init__(self, retries: int = 3):
        self.retries = retries
        self.retry_count = 0
        self.failed_steps = 0

    def step(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                return fn(FakeStepContext(), *args, **kwargs)
            except Exception as e:
                last_exc = e
                # Si falló y aún quedan intentos, cuenta como retry.
                if attempt < self.retries:
                    self.retry_count += 1
                print(
                    f"[local_retry] step={getattr(fn, '__name__', str(fn))} "
                    f"attempt={attempt}/{self.retries} error={e}"
                )
        # Si llegamos aquí, el step falló definitivamente.
        self.failed_steps += 1
        assert last_exc is not None
        raise last_exc


def _experiments_paths() -> tuple[str, str]:
    """
    Devuelve (experiments_dir, csv_path) apuntando a:
      <repo>/experiments/phase2_video_runs.csv
    """
    here = os.path.dirname(__file__)  # .../src/video_pipeline
    repo_root = os.path.abspath(os.path.join(here, "..", ".."))  # .../<repo>
    experiments_dir = os.path.join(repo_root, "experiments")
    csv_path = os.path.join(experiments_dir, "phase2_video_runs.csv")
    return experiments_dir, csv_path


def _ensure_csv(csv_path: str) -> None:
    if os.path.exists(csv_path):
        return
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "mode", "n_chunks", "store_ops", "retries", "time_ms"])


def _append_row(csv_path: str, row: list[Any]) -> None:
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)


def main() -> None:
    ctx = FakeContext(retries=5)

    start = time.time()
    out = run_video_pipeline(
        ctx,
        video_uri="s3://fake-bucket/input/sample.mp4",
        chunk_s=1,
        fail_rate=0.0,  # pon 0.1 / 0.3 para ver retries
    )
    elapsed_ms = int((time.time() - start) * 1000)

    print("\nRESULT:", out)

    # --- Experiments logging ---
    experiments_dir, csv_path = _experiments_paths()
    os.makedirs(experiments_dir, exist_ok=True)
    _ensure_csv(csv_path)

    run_id = str(uuid.uuid4())[:8]
    n_chunks = int(out.get("n_chunks", 0))

    # En durable-local no usamos store explícito; store_ops=0.
    store_ops = 0
    retries = int(ctx.retry_count)

    _append_row(
        csv_path,
        [run_id, "durable-local", n_chunks, store_ops, retries, elapsed_ms],
    )

    print(f"[experiments] wrote: {csv_path}")


if __name__ == "__main__":
    main()

