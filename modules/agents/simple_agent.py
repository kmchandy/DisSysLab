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
from components.sinks.sink_list_collector import ListCollector

# ============================================================================
# Custom Multi-Port Agent
# ============================================================================


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
# Sinks (Output Handlers)
# ============================================================================


# ============================================================================
# Build Network
# ============================================================================
# Create sources
source_x_data = ListSource([10, 20, 30], name="source_x")
source_y_data = ListSource([1, 2, 3], name="source_y")

source_x = Source(ListSource([10, 20, 30], name="source_x").run)
source_y = Source(ListSource([1, 2, 3], name="source_y").run)

# Create the adder agent
adder = Adder()

store_sums = ListCollector()
sink_sums = Sink(store_sums.run)

store_diffs = ListCollector()
sink_diffs = Sink(store_diffs.run)

# Define network topology using port attribute syntax
# agent.port_name automatically creates PortReference(agent, "port_name")
g = network([
    # Connect sources to adder's specific input ports
    (source_x, adder.x),      # adder.x → PortReference(adder, "x")
    (source_y, adder.y),      # adder.y → PortReference(adder, "y")

    # Connect adder's output ports to sinks
    # adder.sum → PortReference(adder, "sum")
    (adder.sum, sink_sums),
    # adder.diff → PortReference(adder, "diff")
    (adder.diff, sink_diffs)
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
    print("Collected sums:", store_sums.values)
    print("Collected diffs:", store_diffs.values)
    print()

    # Verify results
    assert store_sums.values == [
        11, 22, 33], f"Expected [11, 22, 33], got {store_sums.values}"
    assert store_diffs.values == [
        9, 18, 27], f"Expected [9, 18, 27], got {store_diffs.values}"

    print("✓ Multi-port agent test passed!")
    print("=" * 60)
