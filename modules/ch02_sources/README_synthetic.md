<!-- modules/ch02_sources/README_synthetic.md    -->

# 2.9 • Synthetic Numeric Sourc

This page shows how to generate a **synthetic numeric stream** as a source. You may want to test your distributed system against a synthetic input data stream before connecting your system to a streaming souce. 

In this example, the signal is a **noisy sum of sine waves** (e.g., 5 Hz, 12 Hz, 30 Hz plus Gaussian noise), emitted at a fixed sample rate. You can specify the amplitude and phase shift for each frequency.

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
from dsl.connectors.sine_mixture_source import SineMixtureSource
from dsl.connectors.sink_plot_print_numerical_stream import PlotPrintNumericalStream

# Specify the source that generates a mixture of sine waves
src = SineMixtureSource(
    sample_rate=50.0,
    duration_s=2.0,
    components=(
        (2.0, 1.0, 0.0),     # (freq_hz, amplitude, phase_rad)
        (7.0, 0.4, 0.75),
    ),
    noise_std=0.05,          # standard deviation of added Gaussian noise
    seed=123,                # for repeatability of Gaussian noise
    realtime=False,          # generate quickly for the test; no wait between samples
    name="demo_sines",
)

# Specify the sink to print and plot the output
snk = PlotPrintNumericalStream(
    every_n=20,            # print every every_n samples
    first_k=10,            # print all of the first_k samples
    expected_n=100,        # expected number for plotting = sample_rate*duration_s
    title="Sine Mixture Source Output",
    name="sink",
)

# Define and run the network
g = network([(src.run, snk.run)])
g.run_network()

# Plot after network terminates execution
snk.finalize()
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
