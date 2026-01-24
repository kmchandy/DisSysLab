# modules/agents/simple_agent.py

"""
Multi-Port Agent Example: Adder with Two Inputs and Two Outputs

This example demonstrates how to create custom agents with multiple input
and output ports when the simple source/transform/sink pattern isn't sufficient.

Key Concepts:
- Custom Agent subclass with multiple ports
- Receiving from specific named ports
- Sending to specific named ports
- Coordinated input from multiple sources
- Port reference syntax: agent.port_name
"""

from dsl import network
from dsl.core import Agent, STOP
from dsl.blocks import Source, Sink
from components.sources.list_source import ListSource


class Adder(Agent):
    """
    Agent with two input ports and two output ports.

    Ports:
    - Inports: ["x", "y"] - receives numbers to add/subtract
    - Outports: ["sum", "diff"] - sends sum and difference

    Behavior:
    1. Wait for message on port "x"
    2. Wait for message on port "y"
    3. Send (x + y) to port "sum"
    4. Send (x - y) to port "diff"
    5. Repeat until STOP received on either input
    """

    def __init__(self):
        super().__init__(inports=["x", "y"], outports=["sum", "diff"])

    def run(self):
        """Main processing loop."""
        while True:
            # Wait for value on port "x"
            val_x = self.recv("x")
            if val_x is STOP:
                self.broadcast_stop()
                return

            # Wait for value on port "y"
            val_y = self.recv("y")
            if val_y is STOP:
                self.broadcast_stop()
                return

            # Compute and send results
            self.send(msg=val_x + val_y, outport="sum")
            self.send(msg=val_x - val_y, outport="diff")


# ============================================================================
# Build Network
# ============================================================================
# Make sources
x_source = Source(ListSource([10, 20, 30]).run)
y_source = Source(ListSource([1, 2, 3]).run)

# Make the adder agent
adder = Adder()

# Make sinks
sums, diffs = [], []
def append_to_sums(msg): sums.append(msg)
def append_to_diffs(msg): diffs.append(msg)


# Make the network.
# Explicitly name ports for adder because it is an agent with named ports.
g = network([
    # Connect x_source to adder's input port named "x"
    (x_source, adder.x),   # adder.x means port "x" of adder
    # Connect y_source to adder's input port named "y"
    (y_source, adder.y),   # adder.y means port "y" of  adder

    # Connect adder's output port named "sum" to Sink(append_to_sums)
    # adder.sum means port "sum" of agent adder
    (adder.sum, Sink(append_to_sums)),

    # Connect adder's output port named "diff" to Sink(append_to_diffs)
    # adder.sum means port "sum" of agent adder
    (adder.diff, Sink(append_to_diffs)),
])


# ============================================================================
# Execute and Verify
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Port Adder Example")
    print("=" * 60)
    print()
    print("Input X: [10, 20, 30]")
    print("Input Y: [1, 2, 3]")
    print()
    print("Results:")
    print("-" * 60)

    g.run_network()

    print("-" * 60)
    print()
    print("Collected sums:", sums)
    print("Collected diffs:", diffs)
    print()

    # Verify results
    assert sums == [
        11, 22, 33], f"Expected [11, 22, 33], got {sums}"
    assert diffs == [
        9, 18, 27], f"Expected [9, 18, 27], got {diffs}"

    print("✓ Multi-port agent test passed!")
    print("=" * 60)
