from dsl import network


def sine_mixture_source(*, sample_rate=200.0, duration_s=2.0, tones=((5.0, 1.0),), noise_std=0.1):
    import time
    import math
    import numpy as np
    n_total = int(duration_s * sample_rate)
    dt = 1.0 / sample_rate
    t = 0.0
    tones = list(tones)
    for _ in range(n_total):
        x = sum(a * math.sin(2*math.pi*f*t)
                for f, a in tones) + np.random.normal(scale=noise_std)
        yield {"t": t, "x": float(x)}
        t += dt
        time.sleep(dt)

# --- sink that prints every N messages so it doesn’t spam ---


def make_live_console_sink(every_n=20):
    i = 0

    def _sink(msg):
        nonlocal i
        i += 1
        if i % every_n == 0:
            print(f"t={msg['t']:6.3f}  x={msg['x']:+8.4f}")
        return msg
    return _sink


live_console_sink = make_live_console_sink(every_n=20)

g = network([(sine_mixture_source, live_console_sink)])
g.run_network()
