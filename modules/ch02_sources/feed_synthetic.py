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
