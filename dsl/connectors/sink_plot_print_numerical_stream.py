class PlotPrintNumericalStream:
    """
    Sink that:
      - prints every_n samples (and optionally first_k samples),
      - collects t/x,
      - after the run: sanity-checks and plots.
    """

    def __init__(
            self,
            every_n: int = 20,
            first_k: int = 10,
            expected_n: int | None = None,
            title: str = "Plot Title",
            name: str = "PlotPrintNumericalStream"):
        self.every_n = int(every_n)
        self.first_k = int(first_k)
        self.expected_n = expected_n
        self.title = title
        self.name = name

        self.i = 0
        self.t = []
        self.x = []

    def __call__(self, msg):
        # msg expected: {"t": float, "x": float}
        # t is time, x is numerical value in stream
        self.i += 1

        tt = msg["t"]
        xx = msg["x"]

        self.t.append(tt)
        self.x.append(xx)

        if self.i <= self.first_k:
            print(f"i = {self.i:02d}   t={tt:.4f}  x={xx:+.6f}")
        elif self.every_n > 0 and (self.i % self.every_n == 0):
            print(f"i = {self.i:02d}  t={tt:6.3f}  x={xx:+8.4f}")

        return msg

    def finalize(self):
        import math

        n = len(self.t)
        if self.expected_n is not None:
            assert n == self.expected_n, f"Expected {self.expected_n} samples, got {n}"
        assert n > 0, "No samples collected"
        assert self.t[0] == 0.0, "First timestamp should be 0.0"
        assert all(self.t[i] < self.t[i + 1]
                   for i in range(n - 1)), "t must be strictly increasing"
        assert all(math.isfinite(v)
                   for v in self.x), "Found NaN or inf in x values"

        try:
            import matplotlib.pyplot as plt

            plt.figure()
            plt.plot(self.t, self.x)
            plt.title(self.title)
            plt.xlabel("t")
            plt.ylabel("x")
            plt.show()
        except Exception as e:
            print(f"(Plot skipped: {e})")

    run = __call__
