# /examples/numpy_pi_demo.py

from dsl.graph import Graph
import matplotlib.pyplot as plt
from typing import Iterator, Any, Dict, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")       # non-GUI backend; safe in threads

# ---------------------------------------------------------------
#   GENERATE RANDOM NUMBERS: SOURCE
# ---------------------------------------------------------------


def rng_points(*, num_batches: int = 5, batch_size: int = 100, seed: int = 0) -> Iterator[np.ndarray]:
    """Emit batches of uniform points in [0,1]^2 as (N,2) arrays."""
    rng = np.random.default_rng(seed)
    for _ in range(num_batches):
        yield rng.random((batch_size, 2))

# ---------------------------------------------------------------
#   ESTIMATE PI: TRANSFORM
# ---------------------------------------------------------------


def estimate_pi(points: np.ndarray) -> float:
    """Vectorized π estimate from one batch using the quarter-circle test."""
    inside = (points[:, 0]**2 + points[:, 1]**2) <= 1.0
    return 4.0 * np.count_nonzero(inside) / points.shape[0]

# ---------------------------------------------------------------
#   SINK
# ---------------------------------------------------------------


def to_results(msg: Any) -> None:
    results.append(msg)


# ---------------------------------------------------------------
#  GRAPH
# ---------------------------------------------------------------
results: list = []
plot_state = {"plotted": 0}

g = Graph(
    edges=[("src", "pi"), ("pi", "snk")],
    nodes=[("src", rng_points),  # ("plot", plot_points),
           ("pi", estimate_pi), ("snk", to_results),]
)


if __name__ == "__main__":
    g.compile_and_run()

    print("Batch π estimates:", results)
    print("Mean estimate:", float(np.mean(results)))
