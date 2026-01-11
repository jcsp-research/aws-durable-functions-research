# src/counter/steps.py
from __future__ import annotations

import random
from typing import Any

# Import opcional del SDK durable
try:
    from aws_durable_execution_sdk_python import durable_step, StepContext  # type: ignore
except ModuleNotFoundError:
    StepContext = Any

    def durable_step(fn):  # type: ignore
        """
        Decorador no-op para ejecución local.
        En AWS será reemplazado por el real.
        """
        return fn


@durable_step
def init_value(step_context: StepContext, initial: int = 0) -> int:
    """
    Step para inicializar el estado (valor) de forma checkpointed.
    En local: se ejecuta como función normal.
    En AWS: queda checkpointed.
    """
    # logger solo existe en AWS durable
    if hasattr(step_context, "logger"):
        step_context.logger.info(f"[step:init_value] initial={initial}")
    return int(initial)


@durable_step
def apply_delta(step_context: StepContext, current: int, delta: int) -> int:
    """
    Step puro: dado current y delta devuelve el nuevo valor.
    """
    new_value = int(current) + int(delta)
    if hasattr(step_context, "logger"):
        step_context.logger.info(
            f"[step:apply_delta] {current} + ({delta}) = {new_value}"
        )
    return new_value


@durable_step
def get_value(step_context: StepContext, current: int) -> int:
    """
    Step de lectura (lo hacemos step para poder medir replay overhead).
    """
    if hasattr(step_context, "logger"):
        step_context.logger.info(f"[step:get_value] current={current}")
    return int(current)


@durable_step
def flaky_step(step_context: StepContext, fail_rate: float = 0.3) -> str:
    """
    Step para simular fallos transitorios.
    La aleatoriedad es válida dentro del step (queda checkpointed en AWS).
    """
    r = random.random()
    if hasattr(step_context, "logger"):
        step_context.logger.info(
            f"[step:flaky_step] r={r:.4f} fail_rate={fail_rate}"
        )
    if r < fail_rate:
        raise RuntimeError("Simulated transient failure in flaky_step")
    return "ok"

