"""Isolated request context shared by CLI contracts and the service."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationRuntime:
    env: Any
    mode: str
    token: str = ""
    profiles: list = field(default_factory=list)
    output: Any = None
    plan: dict | None = None
    report: dict | None = None


current_runtime: ContextVar[OperationRuntime | None] = ContextVar(
    "ads_runtime", default=None
)


@contextmanager
def operation_runtime(runtime):
    handle = current_runtime.set(runtime)
    try:
        yield runtime
    finally:
        current_runtime.reset(handle)
