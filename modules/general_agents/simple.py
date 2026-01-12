# modules/general_agents/simple.py

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
from dsl.decorators import source_map, sink_map


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

            # Extract the actual numbers from the message dicts
            x = val_x["value"]
            y = val_y["value"]

            # Compute and send results
            self.send({"result": x + y}, "sum")
            self.send({"result": x - y}, "diff")


# ============================================================================
# Data Sources
# ============================================================================

class NumberSource:
    """Generates a sequence of numbers."""

    def __init__(self, numbers, name="source"):
        self.numbers = numbers
        self.name = name
        self.index = 0

    def run(self):
        """Returns next number or None when exhausted."""
        if self.index >= len(self.numbers):
            return None
        num = self.numbers[self.index]
        self.index += 1
        return num


# ============================================================================
# Sinks (Output Handlers)
# ============================================================================

sums = []
diffs = []


def collect_sum(result):
    """Collect sum results."""
    sums.append(result)
    print(f"Sum: {result}")


def collect_diff(result):
    """Collect difference results."""
    diffs.append(result)
    print(f"Diff: {result}")


# ============================================================================
# Build Network
# ============================================================================

# Create sources
source_x_data = NumberSource([10, 20, 30], name="source_x")
source_y_data = NumberSource([1, 2, 3], name="source_y")

source_x = source_map(output_keys=["value"])(source_x_data.run)
source_y = source_map(output_keys=["value"])(source_y_data.run)

# Create the adder agent
adder = Adder()

# Create sinks
display_sums = sink_map(input_keys=["result"])(collect_sum)
display_diffs = sink_map(input_keys=["result"])(collect_diff)

# Define network topology using port attribute syntax
# agent.port_name automatically creates PortReference(agent, "port_name")
g = network([
    # Connect sources to adder's specific input ports
    (source_x, adder.x),      # adder.x → PortReference(adder, "x")
    (source_y, adder.y),      # adder.y → PortReference(adder, "y")

    # Connect adder's output ports to sinks
    (adder.sum, display_sums),    # adder.sum → PortReference(adder, "sum")
    (adder.diff, display_diffs)   # adder.diff → PortReference(adder, "diff")
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
    assert sums == [11, 22, 33], f"Expected [11, 22, 33], got {sums}"
    assert diffs == [9, 18, 27], f"Expected [9, 18, 27], got {diffs}"

    print("✓ Multi-port agent test passed!")
    print("=" * 60)
