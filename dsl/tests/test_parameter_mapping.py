import unittest
from dsl.core import SimpleAgent, Network


class TestParameterMapping(unittest.TestCase):

    def test_parameter_mapping(self):
        """
        Network N passes parameter 'x' to subblock A as 'a' and to B as 'b'.
        A prints its received value and sends it to B, which multiplies it by 2.
        """

        output = []

        def init_A(self, a):
            self.send(a, "out")

        def handle_B(self, msg, b):
            output.append(msg * b)

        # Define inner blocks A and B
        A = SimpleAgent(
            name="A",
            outports=["out"],
            init_fn=init_A,
            parameters={"a": None},  # Will be set by parameter_map
        )

        B = SimpleAgent(
            name="B",
            inport="in",
            handle_msg=handle_B,
            parameters={"b": None},  # Will be set by parameter_map
        )

        # Define network with parameter x mapped to A.a and B.b
        net = Network(
            name="N",
            inports=[],
            outports=[],
            blocks={"A": A, "B": B},
            connections=[("A", "out", "B", "in")],
            parameters={"x": 3},
            parameter_map=[
                ("x", "A", "a"),
                ("x", "B", "b"),
            ],
        )

        net.compile(parameters={"x": 3})
        net.run()

        self.assertEqual(output, [9])  # 3 from A, times 3 in B


if __name__ == "__main__":
    unittest.main()
