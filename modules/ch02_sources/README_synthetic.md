<!-- modules/ch02_sources/README_synthetic.md    -->

# 2.9 • Synthetic Numeric Sourc

This page shows how to generate a **synthetic numeric stream** as a source. You may want to test your distributed system against a synthetic input data stream before connecting your system to a streaming souce. 

In this example, the signal is a **noisy sum of sine waves** (e.g., 5 Hz, 12 Hz, 30 Hz plus Gaussian noise), emitted at a fixed sample rate.

---

## What you’ll do
Create a network with an agent that outputs  `{"t", "x"}` messages in real time (time in seconds, value as a float) and and an agent that prints a line every _N_ messages to the console.

---

## Setup (once)
```bash
pip install numpy rich
```

---

## The Synthetic Source Demo

```python
# modules.ch02_sources.feed_synthetic

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
        x = sum(a * math.sin(2*math.pi*f*t) for f, a in tones) + np.random.normal(scale=noise_std)
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

# Define and run the network
g = network([(sine_mixture_source, live_console_sink)])
g.run_network()
```

---

## Run the demo
Execute the following from the DisSysLab directory:
```bash
python -m modules.ch02_sources.feed_synthetic
```

You’ll see periodic lines like:
```
t=  0.100  x=  +0.2145
t=  0.200  x=  -0.5821
t=  0.300  x=  +0.9473
...
```

---

## Parameters you can modify

| Parameter | Type | Description |
|-----------|------|-------------|
| **sample_rate** | float | Samples per second (e.g., `200.0`). Controls pacing (`time.sleep(1/sample_rate)`). |
| **duration_s** | float | Total duration to emit (seconds). |
| **tones** | list\[tuple(freq_hz, amplitude)\] | Sine components that are summed (e.g., `((5.0, 1.0), (12.0, 0.6), (30.0, 0.3))`). |
| **noise_std** | float | Standard deviation of added Gaussian noise. |
| **every_n** | int | Console prints every N messages to reduce spam. |

> _Note:_ This source produces a **noisy sum of sine waves** and is ideal for testing numeric transformers (filters, spectra, anomaly detectors).

---

## Troubleshooting

- **No output:** Lower `every_n` (e.g., `5`) or temporarily print every message.  
- **Runs too fast/slow:** Adjust `sample_rate` (and `duration_s`).  
- **Choppy timing on some OSes:** `time.sleep` isn’t real-time; it’s fine for demos. Increase `every_n` to reduce console overhead.

---

## 👉 Next
[**Transformers using AI**  →](../ch03_GPT/README_1.md). See how you can use OpenAI and other AI providers to create transformers.
