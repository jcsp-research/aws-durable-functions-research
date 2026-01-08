# src/video_pipeline/local_run.py
from __future__ import annotations

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
      - context.step(fn, *args)
      - retries (durable-like) en steps que fallen
    """
    def __init__(self, retries: int = 3):
        self.retries = retries

    def step(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                return fn(FakeStepContext(), *args, **kwargs)
            except Exception as e:
                last_exc = e
                print(
                    f"[local_retry] step={getattr(fn, '__name__', str(fn))} "
                    f"attempt={attempt}/{self.retries} error={e}"
                )
        assert last_exc is not None
        raise last_exc


def main():
    ctx = FakeContext(retries=5)
    out = run_video_pipeline(
        ctx,
        video_uri="s3://fake-bucket/input/sample.mp4",
        chunk_s=1,
        fail_rate=0.0,  # prueba fallos
    )
    print("\nRESULT:", out)


if __name__ == "__main__":
    main()

