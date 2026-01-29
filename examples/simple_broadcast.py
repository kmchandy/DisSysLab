# dsl.examples.graph_pipeline

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Sink, Transform

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================
list_source = ListSource(items=["hello", "world"])
results_0 = []
results_1 = []

# ==============================================================================
# STEP 2: Wrap Functions in Network Blocks
# ==============================================================================
# Transform ordinary functions into network nodes.
# Each block is an independent processing unit that can run concurrently.
source = Source(
    fn=list_source.run,
    name="list_source"
)
collector_0 = Sink(
    fn=results_0.append,
    name="collector_0"
)
collector_1 = Sink(
    fn=results_1.append,
    name="collector_1"
)

# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Specify the network as a list of edges. Each edge (x, y) connects the output
# of node x to the input of node y.

g = network([(source, collector_0), (source, collector_1)])
g.run_network()

if __name__ == "__main__":
    assert results_0 == ['hello', 'world']
    assert results_1 == ['hello', 'world']
    print("✓ simple_broadcast completed successfully!")
