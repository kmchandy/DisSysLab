# test/test_basic_network.py

import unittest
from queue import SimpleQueue
from dsl.core import Network, SimpleAgent


class TestBasicNetwork(unittest.TestCase):

    def test_message_flow(self):
        """
        Create a simple network A -> B -> C.
        A sends a value, B increments it, C stores it.
        """

        results = []

        def generator(agent):
            agent.send(1, "out")
            agent.send("__STOP__", "out")

        def increment(agent, msg, **params):
            agent.send(msg + 1, "out")

        def collect(agent, msg, **params):
            results.append(msg)

        net = Network(
            name="test_net",
            parameters={},
            blocks={
                "A": SimpleAgent(name="A", outports=["out"], init_fn=generator),
                "B": SimpleAgent(name="B", inport="in", outports=["out"], handle_msg=increment),
                "C": SimpleAgent(name="C", inport="in", handle_msg=collect)
            },
            connections=[
                ("A", "out", "B", "in"),
                ("B", "out", "C", "in")
            ]
        )

        net.compile({})
        net.run()

        self.assertEqual(results, [2])  # 1 (from A) + 1 (increment in B) = 2

    def test_parameters_passed(self):
        result = []

        def handler(agent, msg, **params):
            result.append(params["scale"] * msg)

        agent = SimpleAgent(
            name="scale_agent",
            inport="in",
            outports=[],
            handle_msg=handler,
            parameters={"scale": 3}
        )

        # Simulate connection and message
        q = SimpleQueue()
        agent.in_q["in"] = q
        q.put(5)
        q.put("__STOP__")
        agent.run()

        self.assertEqual(result, [15])  # 3 * 5


if __name__ == "__main__":
    unittest.main()
