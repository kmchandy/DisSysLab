# modules/agents/simple_split.py

"""
Test Split agent with round-robin routing.

Generates numbers 0 to 9 and routes them round-robin to 3 output files.
Expected distribution:
- file_0.txt: 0, 3, 6, 9
- file_1.txt: 1, 4, 7
- file_2.txt: 2, 5, 8
"""

from dsl.blocks import Source, Split, Sink
from dsl import network
from components.sinks.sink_simple_file import FileLineWriter
from components.sources.natural_numbers_source import NaturalNumberGenerator


class RoundRobinRouter:
    """Routes messages round-robin across N outputs"""

    def __init__(self, num_outputs=3):
        self.num_outputs = num_outputs
        self.counter = 0

    def run(self, msg):
        """
        Route message to one output based on counter.
        Returns list of N messages where only one of the N messages is non-None.
        The k-th message in the list is the message for the k-th output port of Split.
        If the input message stream is [0, 1, 2, 3] then the output stream is
        [
            [0, None, None],
            [None, 1, None],
            [None, None, 2],
            [3, None, None]
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


# ============================================================================
# Build the Network
# ============================================================================
# Create source
num_gen = NaturalNumberGenerator(max_count=10)
source = Source(fn=num_gen.run, name="number_generator")

# Create split with round-robin router
router = RoundRobinRouter(3)
# num_outputs must be specified for splitter
splitter = Split(fn=router.run, num_outputs=3, name="round_robin_splitter")

# Create three file writer sinks
writer0 = FileLineWriter("file_0.txt")
writer1 = FileLineWriter("file_1.txt")
writer2 = FileLineWriter("file_2.txt")

sink0 = Sink(fn=writer0.run, name="sink_0")
sink1 = Sink(fn=writer1.run, name="sink_1")
sink2 = Sink(fn=writer2.run, name="sink_2")

# Build network topology
g = network([
    (source, splitter),
    (splitter.out_0, sink0),
    (splitter.out_1, sink1),
    (splitter.out_2, sink2),
])


# ============================================================================
# Step 5: Run the Network
# ============================================================================

if __name__ == "__main__":
    print("Running split test with round-robin routing...")
    print("Generating numbers 0-9 and routing to 3 files")
    print()

    g.run_network()

    print()
    print("Done! Check the output files:")
    print("  file_0.txt should contain: 0, 3, 6, 9")
    print("  file_1.txt should contain: 1, 4, 7")
    print("  file_2.txt should contain: 2, 5, 8")
