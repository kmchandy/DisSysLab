import time
import math
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple
import numpy as np


class SineMixtureSource:
    """
    Stream a mixture of sine waves plus Gaussian noise.

    Option B specification:
        components = ((f_hz, amplitude, phase_rad), ...)

    Yields dict messages:
        {"t": t_seconds, "x": float_value}

    Notes:
      - phase is in radians
      - realtime=True paces output to sample_rate using a monotonic clock
      - realtime=False generates as fast as possible (useful for tests)
      - seed makes noise reproducible
    """

    def __init__(
        self,
        sample_rate: float = 200.0,
        duration_s: float = 2.0,
        components: Sequence[Tuple[float, float, float]] = ((5.0, 1.0, 0.0),),
        noise_std: float = 0.1,
        seed: Optional[int] = None,
        realtime: bool = True,
        name: Optional[str] = None,
    ):
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be > 0, got {sample_rate}")
        if duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {duration_s}")
        if noise_std < 0:
            raise ValueError(f"noise_std must be >= 0, got {noise_std}")
        if len(components) == 0:
            raise ValueError("components must be non-empty")

        self.sample_rate = float(sample_rate)
        self.duration_s = float(duration_s)
        self.noise_std = float(noise_std)
        self.realtime = bool(realtime)
        self.name = name or self.__class__.__name__

        # Validate and normalize components
        comps = []
        for c in components:
            if len(c) != 3:
                raise ValueError(
                    "Each component must be a 3-tuple (freq_hz, amplitude, phase_rad). "
                    f"Got: {c}"
                )
            f, a, ph = float(c[0]), float(c[1]), float(c[2])
            comps.append((f, a, ph))
        self.components = tuple(comps)

        # Reproducible RNG
        self._rng = np.random.default_rng(seed)

        # Precompute angular frequencies
        two_pi = 2.0 * math.pi
        self._terms = tuple((two_pi * f, a, ph)
                            for (f, a, ph) in self.components)

    def __call__(self) -> Iterator[Dict[str, Any]]:
        n_total = int(round(self.duration_s * self.sample_rate))
        dt = 1.0 / self.sample_rate
        t = 0.0

        if self.realtime:
            start = time.perf_counter()
            next_deadline = start

            for _ in range(n_total):
                x = math.fsum(a * math.sin(omega * t + ph)
                              for omega, a, ph in self._terms)
                if self.noise_std > 0.0:
                    x += float(self._rng.normal(0.0, self.noise_std))

                yield {"t": t, "x": float(x)}

                t += dt
                next_deadline += dt

                now = time.perf_counter()
                sleep_s = next_deadline - now
                if sleep_s > 0:
                    time.sleep(sleep_s)
        else:
            for _ in range(n_total):
                x = math.fsum(a * math.sin(omega * t + ph)
                              for omega, a, ph in self._terms)
                if self.noise_std > 0.0:
                    x += float(self._rng.normal(0.0, self.noise_std))
                yield {"t": t, "x": float(x)}
                t += dt

    run = __call__


if __name__ == "__main__":
    # Simple self-test / demo:
    # 1) Build a 2-tone mixture with phase shifts.
    # 2) Print the first few samples.
    # 3) Run basic sanity checks (no reproducibility assertion).
    # 4) Optionally plot if matplotlib is available.

    src = SineMixtureSource(
        sample_rate=50.0,
        duration_s=2.0,
        components=(
            (2.0, 1.0, 0.0),     # (freq_hz, amplitude, phase_rad)
            (7.0, 0.4, 0.75),
        ),
        noise_std=0.05,
        seed=123,               # keeps this demo repeatable, but not asserted here
        realtime=False,         # generate quickly for the test
        name="demo_sines",
    )

    data_t = []
    data_x = []

    for i, msg in enumerate(src()):
        if i < 10:
            print(f"{i:02d}  t={msg['t']:.4f}  x={msg['x']:+.6f}")
        data_t.append(msg["t"])
        data_x.append(msg["x"])

    # Basic sanity checks
    expected_n = int(round(src.duration_s * src.sample_rate))
    assert len(
        data_t) == expected_n, f"Expected {expected_n} samples, got {len(data_t)}"
    assert data_t[0] == 0.0, "First timestamp should be 0.0"
    assert all(data_t[i] < data_t[i + 1]
               for i in range(len(data_t) - 1)), "t must be strictly increasing"

    # Check x values are finite
    import math
    assert all(math.isfinite(x)
               for x in data_x), "Found NaN or inf in x values"

    # Plot if matplotlib exists (optional)
    try:
        import matplotlib.pyplot as plt

        plt.figure()
        plt.plot(data_t, data_x)
        plt.title("SineMixtureSource demo")
        plt.xlabel("t (s)")
        plt.ylabel("x")
        plt.show()
    except Exception as e:
        print(f"(Plot skipped: {e})")

    print("OK: demo completed.")
