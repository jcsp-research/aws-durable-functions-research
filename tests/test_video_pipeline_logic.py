# tests/test_video_pipeline_logic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import pytest

from video_pipeline.pipeline import run_video_pipeline


class DummyLogger:
    def info(self, msg: str) -> None:
        pass


@dataclass
class FakeStepContext:
    logger: Any = DummyLogger()


class FakeContext:
    def __init__(self, retries: int = 1):
        self.retries = retries

    def step(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        last_exc: Exception | None = None
        for _ in range(self.retries):
            try:
                return fn(FakeStepContext(), *args, **kwargs)
            except Exception as e:
                last_exc = e
        assert last_exc is not None
        raise last_exc


@pytest.fixture
def ctx():
    return FakeContext(retries=3)


def test_pipeline_success(ctx):
    out = run_video_pipeline(ctx, video_uri="s3://x/in.mp4", chunk_s=1, fail_rate=0.0)
    assert out["ok"] is True
    assert out["n_chunks"] == 10
    assert out["final"]["output_uri"].endswith("final.mp4")
    # chunks ordenados
    chunk_ids = [c["chunk_id"] for c in out["final"]["chunks"]]
    assert chunk_ids == sorted(chunk_ids)


def test_pipeline_fails_when_always_failing():
    ctx_fail = FakeContext(retries=2)
    with pytest.raises(RuntimeError):
        run_video_pipeline(ctx_fail, video_uri="s3://x/in.mp4", chunk_s=1, fail_rate=1.0)

