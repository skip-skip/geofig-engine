from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd


@dataclass(frozen=True)
class PipelineStep:
    name: str
    func: Callable[[pd.DataFrame], pd.DataFrame]
    kwargs: dict[str, Any] = field(default_factory=dict)


class Pipeline:
    def __init__(self, steps: list[PipelineStep] | None = None) -> None:
        self._steps: list[PipelineStep] = list(steps or [])

    def add(self, name: str, func: Callable[[pd.DataFrame], pd.DataFrame], **kwargs: Any) -> Pipeline:
        self._steps.append(PipelineStep(name=name, func=func, kwargs=kwargs))
        return self

    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        result = data
        for step in self._steps:
            result = step.func(result, **step.kwargs)
        return result

    @property
    def steps(self) -> list[PipelineStep]:
        return list(self._steps)
