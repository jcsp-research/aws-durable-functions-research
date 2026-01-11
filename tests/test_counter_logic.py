# tests/test_counter_logic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from counter.counter_app import run_counter_workflow


class DummyLogger:
    def info(self, msg: str) -> None:
        # Para tests no hace falta imprimir
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


@dataclass
class FakeStepContext:
    logger: Any = DummyLogger()


class FakeContext:
    """
    Contexto local mínimo compatible con:
        context.step(fn, *args)
    """
    def step(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return fn(FakeStepContext(), *args, **kwargs)


@pytest.fixture
def ctx():
    return FakeContext()


def test_batch_ordering(ctx):
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
    assert out["value"] == 2
    assert out["executed"] == [
        ("increment", 1),
        ("increment", 2),
        ("get", 0),
        ("decrement", 1),
    ]


def test_simple_increment(ctx):
    out = run_counter_workflow(ctx, op="increment", amount=3, initial=10, commands=None)
    assert out["value"] == 13
    assert out["executed"] == [("increment", 3)]


def test_simple_decrement(ctx):
    out = run_counter_workflow(ctx, op="decrement", amount=4, initial=10, commands=None)
    assert out["value"] == 6
    assert out["executed"] == [("decrement", 4)]


def test_get(ctx):
    out = run_counter_workflow(ctx, op="get", amount=1, initial=7, commands=None)
    assert out["value"] == 7
    assert out["executed"] == [("get", 0)]


def test_unknown_op_raises(ctx):
    with pytest.raises(ValueError):
        run_counter_workflow(ctx, op="nope", amount=1, initial=0, commands=None)


def test_flaky_can_fail(ctx):
    # fail_rate=1.0 garantiza fallo
    with pytest.raises(RuntimeError):
        run_counter_workflow(
            ctx,
            op="get",
            amount=1,
            initial=0,
            commands=[
                {"op": "increment", "amount": 1},
                {"op": "flaky", "fail_rate": 1.0},
            ],
        )

