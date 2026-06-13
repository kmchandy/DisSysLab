#!/usr/bin/env python3
"""Generate the ``points.txt`` file used by ``recovery_demo``.

Pure standard library. Run from this folder::

    python make_points.py

Writes 10 000 uniformly random ``(x, y)`` pairs in ``[0, 1]^2``,
one per line, comma-separated. Deterministic — the seed is fixed
so every reader gets the same trajectory of the Monte Carlo π
estimator.
"""

from __future__ import annotations

import random
from pathlib import Path


N = 10_000
SEED = 42


def main() -> None:
    here = Path(__file__).resolve().parent
    out = here / "points.txt"
    rng = random.Random(SEED)
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# {N} random (x, y) pairs in [0, 1]^2, seed={SEED}\n")
        for _ in range(N):
            x = rng.random()
            y = rng.random()
            f.write(f"{x:.6f},{y:.6f}\n")
    print(f"Wrote {N} points to {out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
