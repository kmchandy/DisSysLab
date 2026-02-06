"""
Split Example - Round-Robin Message Routing

This example demonstrates the split pattern:
- One source sends messages to a splitter
- The splitter routes each message to ONE of multiple outputs
- Routing logic determines which output gets which message

Data flow:
                    → out_0 → collector_0 → [0, 3, 6, 9]
    [0..9] → splitter → out_1 → collector_1 → [1, 4, 7]
                    → out_2 → collector_2 → [2, 5, 8]

Round-robin: message N goes to output (N % 3)
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Split, Sink

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

number_source = ListSource(items=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


class RoundRobinRouter:
    """Routes messages round-robin across N outputs."""

    def __init__(self, num_outputs=3):
        self.num_outputs = num_outputs
        self.counter = 0

    def run(self, msg):
        """
        Route message to one output based on counter.

        Returns a list of N messages where only one is non-None.
        The k-th element in the list is the message for the k-th output port.

        Example: if input stream is [0, 1, 2, 3], output stream is:
        [
            [0, None, None],     # 0 goes to output 0
            [None, 1, None],     # 1 goes to output 1
            [None, None, 2],     # 2 goes to output 2
            [3, None, None]      # 3 goes to output 0 (wraps around)
        ]
        """
        # Create result list with None for all positions
        results = [None] * self.num_outputs

        # Put message at current position
        output_index = self.counter % self.num_outputs
        results[output_index] = msg

        # Increment counter for next message
        self.counter += 1

        return results


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Source node: generates numbers 0-9
source = Source(
    fn=number_source.run,
    name="number_source"
)

# Split node: routes messages round-robin to 3 outputs
router = RoundRobinRouter(num_outputs=3)
splitter = Split(
    fn=router.run,
    num_outputs=3,  # MUST specify number of outputs
    name="round_robin_splitter"
)

# Sink nodes: collect results from each output
results_0 = []
collector_0 = Sink(
    fn=results_0.append,
    name="collector_0"
)

results_1 = []
collector_1 = Sink(
    fn=results_1.append,
    name="collector_1"
)

results_2 = []
collector_2 = Sink(
    fn=results_2.append,
    name="collector_2"
)


# ==============================================================================
# STEP 3: Build and Run the Network
# ==============================================================================
# Split uses PORT REFERENCES: splitter.out_0, splitter.out_1, splitter.out_2
# Each port connects to a different destination

g = network([
    (source, splitter),
    (splitter.out_0, collector_0),  # Output port 0
    (splitter.out_1, collector_1),  # Output port 1
    (splitter.out_2, collector_2)   # Output port 2
])

# Run the network
g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("Output 0:", results_0)
    print("Output 1:", results_1)
    print("Output 2:", results_2)

    assert results_0 == [0, 3, 6, 9], f"Expected [0, 3, 6, 9], got {results_0}"
    assert results_1 == [1, 4, 7], f"Expected [1, 4, 7], got {results_1}"
    assert results_2 == [2, 5, 8], f"Expected [2, 5, 8], got {results_2}"

    print("✓ Split completed successfully!")
    print(f"  Input: 10 numbers (0-9)")
    print(f"  Output 0: {len(results_0)} numbers (0 mod 3)")
    print(f"  Output 1: {len(results_1)} numbers (1 mod 3)")
    print(f"  Output 2: {len(results_2)} numbers (2 mod 3)")
