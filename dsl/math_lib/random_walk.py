# dsl/math_lib/random_walk.py

from __future__ import annotations
from typing import Optional
import time
import random


class RandomWalkOneDimensional:
    """
    Yields exactly `n_steps` messages: {"t_step": int, "x": float}
    where x is a random walk with drift (drift_per_step), Gaussian noise (standard deviation 
    of sigma), and occasional big jumps with probability prob_jump and std of jump_stdev.
    """

    def __init__(
        self,
        *,
        n_steps: int = 500,           # number of steps of random walk generated
        base: float = 100.0,          # starting value of random walk
        drift_per_step: float = 0.1,  # deterministic drift added to each step
        sigma: float = 1.0,           # stddev of Gaussian noise added to each step
        seed: int = 0,                # random number generator seed for reproducibility
        prob_jump: float = 0.1,       # prob of big jump at a step
        jump_stdev: float = 10.0,    # standard deviation of a big jump
        # time to sleep per step to simulate real-time stream
        sleep_time_per_step: float = 0.0,
        t_key: Optional[str] = "t_step",  # time step key in output dict
        x_key: Optional[str] = "x",      # position key in output dict
        name: Optional[str] = None,   # name of this object
    ) -> None:
        self.n_steps = int(n_steps)
        self.x = float(base)
        self.drift = float(drift_per_step)
        self.sigma = float(sigma)
        self.prob_jump = float(prob_jump)
        self.jump_stdev = float(jump_stdev)
        self.rng = random.Random(seed)  # uniform random number generator
        self.sleep_time_per_step = float(sleep_time_per_step)
        self.t_key = t_key
        self.x_key = x_key
        self._name = name or "src_random_walk"

    @property
    def __name__(self) -> str:
        return self._name

    def __call__(self):
        for i in range(self.n_steps):
            # add drift and Gaussian noise to walk position
            self.x += self.drift
            self.x += self.rng.gauss(0.0, self.sigma)
            # add a big jump with probability prob_jump
            if self.rng.random() < self.prob_jump:
                self.x += self.rng.gauss(0.0, self.jump_stdev)
            yield {self.t_key: i, self.x_key: float(self.x)}
            if self.sleep_time_per_step > 0:
                # simulate real-time stream
                time.sleep(self.sleep_time_per_step)

    run = __call__
