"""
Custom Agent Example - Building Agents from Scratch

This example shows how to create custom agents by subclassing Agent:
1. Sender: Source agent that emits items from a list
2. Uppercase: Transform agent with state (alternates upper/lower case)
3. Receiver: Sink agent that prints messages

Data flow: ["hello", "world", ...] → ALTERNATE CASE → print
"""

from dsl import network, Agent
from dsl.core import STOP


# ==============================================================================
# Custom Agent Classes
# ==============================================================================

class Sender(Agent):
    """
    Source agent that sends items from a list.

    This demonstrates:
    - How to create a source (no inports)
    - How to send messages
    - How to signal completion with broadcast_stop()
    """

    def __init__(self, items: list, name: str):
        super().__init__(name=name, inports=[], outports=["out_"])
        self.items = items

    def run(self):
        # Send each item
        for msg in self.items:
            self.send(msg, "out_")

        # Signal we're done
        self.broadcast_stop()


class Uppercase(Agent):
    """
    Stateful transform agent that alternates between upper and lower case.

    This demonstrates:
    - How to maintain state between messages
    - How to transform messages
    - How to handle STOP and propagate it downstream
    """

    def __init__(self, name: str, start_with_upper: bool = True):
        super().__init__(name=name, inports=["in_"], outports=["out_"])
        self.use_upper = start_with_upper

    def run(self):
        while True:
            # Receive message
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                self.broadcast_stop()
                return

            # Transform based on current state
            output_msg = msg.upper() if self.use_upper else msg.lower()

            # Toggle state for next message
            self.use_upper = not self.use_upper

            # Send transformed message
            self.send(output_msg, "out_")


class Receiver(Agent):
    """
    Sink agent that prints received messages.

    This demonstrates:
    - How to create a sink (no outports)
    - How to receive messages in a loop
    - How to handle STOP (no need to broadcast - no outputs)
    """

    def __init__(self, msgs_received: list, name: str):
        super().__init__(name=name, inports=["in_"], outports=[])
        self.msgs_received = msgs_received

    def run(self):
        while True:
            # Receive message
            msg = self.recv("in_")

            # Check for termination
            if msg is STOP:
                return  # Sink has no outputs, so just stop

            # Perform side effect
            self.msgs_received.append(msg)


# ==============================================================================
# Build and Run Network
# ==============================================================================

sender = Sender(items=["hello", "world", "how", "Are", "YOU"], name="sender")
transformer = Uppercase(name="uppercase", start_with_upper=True)
receiver = Receiver(msgs_received=[], name="receiver")

# Network: sender → transformer → receiver
g = network([
    (sender, transformer),
    (transformer, receiver),
])

g.run_network()
assert receiver.msgs_received == ["HELLO", "world", "HOW", "are", "YOU"]
print(f"Messages received: {receiver.msgs_received}")
print("✓ simple_agent completed successfully!")
