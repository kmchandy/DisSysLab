# dsl/catalog/factories.py
from __future__ import annotations

from typing import Callable, Dict

from dsl.math_lib.random_walk import RandomWalkOneDimensional

# op_id -> factory(**params) -> runnable callable (e.g., obj.run or a function)
FACTORIES: Dict[str, Callable[..., Callable]] = {
    "sources.random_walk_1d": lambda **p: RandomWalkOneDimensional(**p).run,
}
