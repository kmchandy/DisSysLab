import unittest
from dsl.core import SimpleAgent, Network


class TestNestedNetwork(unittest.TestCase):
    """
    Test case for verifying nested networks work correctly.
    """

    def test_nested_network(self):
        """
        Constructs a network of the form:

        OuterNet:
            - A (SimpleAgent) --> InnerNet --> C (SimpleAgent)

        InnerNet:
            - B1 (SimpleAgent) --> B2 (SimpleAgent)
        """

        output = []

        # Agent A: emits a message
        def init_a(self, **kwargs):
            self.send("Hello", "out")
            self.send("__STOP__", "out")

        agent_a = SimpleAgent(
            name="A",
            outports=["out"],
            init_fn=init_a
        )

        # Inner agent B1: adds " B1"
        def handle_b1(self, msg, **kwargs):
            self.send(msg + " B1", "out")

        agent_b1 = SimpleAgent(
            name="B1",
            inport="in",
            outports=["out"],
            handle_msg=handle_b1
        )

        # Inner agent B2: adds " B2"
        def handle_b2(self, msg, **kwargs):
            self.send(msg + " B2", "out")

        agent_b2 = SimpleAgent(
            name="B2",
            inport="in",
            outports=["out"],
            handle_msg=handle_b2
        )

        # Agent C: collects final output
        def handle_c(self, msg, **kwargs):
            output.append(msg)

        agent_c = SimpleAgent(
            name="C",
            inport="in",
            handle_msg=handle_c
        )

        # Inner network
        inner_net = Network(
            name="InnerNet",
            blocks={"B1": agent_b1, "B2": agent_b2},
            connections=[
                ("external", "in", "B1", "in"),
                ("B1", "out", "B2", "in"),
                ("B2", "out", "external", "out")
            ]
        )

        # Outer network
        outer_net = Network(
            name="OuterNet",
            blocks={
                "A": agent_a,
                "Inner": inner_net,
                "C": agent_c
            },
            connections=[
                ("A", "out", "Inner", "in"),
                ("Inner", "out", "C", "in")
            ]
        )

        outer_net.compile()
        outer_net.run()

        self.assertEqual(output, ["Hello B1 B2"])


if __name__ == "__main__":
    unittest.main()
