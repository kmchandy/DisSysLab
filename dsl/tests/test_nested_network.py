import unittest
from dsl.core import SimpleAgent, Agent, Network
from dsl.utils.visualize import print_block_hierarchy, print_graph_connections_only


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
            name="Inner",
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
        print_block_hierarchy(outer_net)
        print_graph_connections_only(outer_net)
        outer_net.run()

        self.assertEqual(output, ["Hello B1 B2"])


class TestNestedNetwork_2(unittest.TestCase):
    def test_network_2(self):

        # Agent a logic
        def init_a(self, p):
            for i in range(p):
                self.send(i, "out")
            self.send("__STOP__", "out")

        # Agent b logic
        def handle_msg_b(self, msg, q):
            self.send(msg=msg+q, outport="out")

        # Agent c logic
        def agent_c_logic(self, **kwargs):
            r = kwargs["r"]
            self.saved = []
            self.port_0_open, self.port_1_open = True, True
            while self.port_0_open or self.port_1_open:
                if self.port_0_open:
                    msg_0 = self.recv('in_0')
                    if msg_0 == "__STOP__":
                        self.port_0_open = False
                        msg_0 = 0
                if self.port_1_open:
                    msg_1 = self.recv('in_1')
                    if msg_1 == "__STOP__":
                        self.port_1_open = False
                        msg_1 = 0
                self.saved.append((msg_0 + msg_1)*r)

        agent_a0 = SimpleAgent(
            name="A0",
            outports=["out"],
            init_fn=init_a,
            parameters={"p": None}
        )

        agent_a1 = SimpleAgent(
            name="A1",
            outports=["out"],
            init_fn=init_a,
            parameters=["p"]
        )

        agent_b0 = SimpleAgent(
            name="B0",
            outports=["out"],
            handle_msg=handle_msg_b,
            parameters=["q"]
        )

        agent_b1 = SimpleAgent(
            name="B1",
            outports=["out"],
            handle_msg=handle_msg_b,
            parameters={"q": None}
        )

        agent_c = Agent(
            name="C",
            inports=["in_0", "in_1"],
            run=agent_c_logic,
            parameters={"r": None}
        )
        agent_c.saved = []

        block_0 = Network(
            name="block_0",
            blocks={"A0": agent_a0, "B0": agent_b0},
            connections=[
                ("A0", "out", "B0", "in"),
                ("B0", "out", "external", "out")
            ],
            parameters={"p": None, "q": None},
            parameter_map=[
                ("p", "A0", "p"),
                ("q", "B0", "q"),
            ]
        )

        block_1 = Network(
            name="block_1",
            blocks={"A1": agent_a1, "B1": agent_b1},
            connections=[
                ("A1", "out", "B1", "in"),
                ("B1", "out", "external", "out")
            ],
            parameters={"p": None, "q": None},
            parameter_map=[
                ("p", "A1", "p"),
                ("q", "B1", "q"),
            ]
        )

        block_top = Network(
            name="block_top",
            blocks={"block_0": block_0, "block_1": block_1, "agent_c": agent_c},
            connections=[
                ("block_0", "out", "agent_c", "in_0"),
                ("block_1", "out", "agent_c", "in_1")
            ],
            parameters={"p": None, "q": None, "r": None},
            parameter_map=[
                ("p", "block_0", "p"),
                ("p", "block_1", "p"),
                ("q", "block_0", "q"),
                ("q", "block_1", "q"),
                ("r", "agent_c", "r"),
            ]
        )

        block_top.compile(parameters={"p": 2, "q": 10, "r": 3})
        print_block_hierarchy(block_top)
        print_graph_connections_only(block_top)
        block_top.run()
        self.assertEqual(agent_c.saved, [60, 66, 0])

    # ---------------------------------------------------------------

        def make_simple_agent_type_1(name):
            return SimpleAgent(
                name=name,
                outports=["out"],
                init_fn=init_a,
                parameters={"p": None}
            )

        def make_simple_agent_type_2(name):
            return SimpleAgent(
                name=name,
                outports=["out"],
                handle_msg=handle_msg_b,
                parameters={"q": None}
            )

        agent_a0 = make_simple_agent_type_1("A0")
        agent_a1 = make_simple_agent_type_1("A1")
        agent_b0 = make_simple_agent_type_2("B0")
        agent_b1 = make_simple_agent_type_2("B1")

        block_top.compile(parameters={"p": 2, "q": 10, "r": 3})
        block_top.run()
        self.assertEqual(agent_c.saved, [60, 66, 0])


if __name__ == "__main__":
    unittest.main()
