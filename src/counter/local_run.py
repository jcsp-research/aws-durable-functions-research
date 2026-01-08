# src/counter/local_run.py
from __future__ import annotations

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


def main():
    ctx = FakeContext()

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

    print("\nRESULT:", out)


if __name__ == "__main__":
    main()

