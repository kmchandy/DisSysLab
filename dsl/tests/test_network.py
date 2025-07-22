import unittest
from dsl.core import RunnableBlock, Network, Agent, SimpleAgent, Distripy


class TestNetwork_0(unittest.TestCase):

    def test_1(self):

        def f(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')
            agent.stop()

        saved = []

        def g(agent, msg):
            saved.append(msg)

        # Create the network. This network has no inports or outports
        # that are visible to other networks.
        net = Network(
            name="Net",
            blocks={"sender": Agent(outports=['out'], run=f),
                    "receiver": SimpleAgent(handle_msg=g)
                    },
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        # Run the network
        s = Distripy(net)
        s.compile()
        s.run()
        self.assertEqual(saved, [0, 1, 2])

    def test_2(self):

        def f(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')
            agent.send(msg='__STOP__', outport='out')

        g_saved = []

        def g(agent):
            while True:
                msg = agent.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    g_saved.append(msg)

        def h(agent):
            while True:
                msg = agent.recv(inport='in')
                if msg == "__STOP__":
                    for outport in agent.outports:
                        agent.send(msg="__STOP__", outport=outport)
                    break
                else:
                    agent.send(msg=2*msg, outport='out')

        # Create the network. This network has no inports or outports
        # that are visible to other networks.
        net = Network(
            name="Net",
            blocks={"sender": Agent(outports=["out"], run=f,),
                    "receiver": Agent(inports=["in"], run=g),
                    "transformer": Agent(inports=["in"], outports=["out"], run=h),
                    },
            connections=[
                ("sender", "out", "transformer", "in"),
                ("transformer", "out", "receiver", "in")
            ]
        )
        # Run the network
        s = Distripy(net)
        s.compile()
        s.run()
        self.assertEqual(g_saved, [0, 2, 4])


class TestNetwork_1(unittest.TestCase):
    def test_network_1(self):

        def init_fn_for_B(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')

        saved_for_C = []

        def handle_msg_for_C(agent, msg):
            saved_for_C.append(msg)

        # Create runnable blocks
        B = SimpleAgent('B', outports=["out"], init_fn=init_fn_for_B)
        C = SimpleAgent('C', handle_msg=handle_msg_for_C)

        # Create subnetwork net_1 with B and output forwarding
        net_1 = Network(
            name="net_1",
            inports=[],
            outports=["out"],
            blocks={"B": B},
            connections=[
                ("B", "out", "external", "out")  # B.out → net_1.out
            ]
        )

        # Create subnetwork net_2 with C and input forwarding
        net_2 = Network(
            name="net_2",
            inports=["in"],
            outports=[],
            blocks={"C": C},
            connections=[
                ("external", "in", "C", "in")  # net_2.in → C.in
            ]
        )

        # Top-level network
        net_0 = Network(
            name="net_0",
            inports=[],
            outports=[],
            blocks={"net_1": net_1, "net_2": net_2},
            connections=[
                ("net_1", "out", "net_2", "in")  # net_1.out → net_2.in
            ]
        )
        s = Distripy(net_0)
        s.compile()
        s.run()
        self.assertEqual(saved_for_C, [0, 1, 2])


class TestFlattenNetwork_2(unittest.TestCase):

    def test_flatten_nested_network_2(self):

        def init_fn_for_B(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')

        saved_for_C = []

        def handle_msg_for_C(agent, msg):
            saved_for_C.append(msg)

        # Create runnable blocks
        B = SimpleAgent('B', outports=["out"], init_fn=init_fn_for_B)
        C = SimpleAgent('C', handle_msg=handle_msg_for_C)

        # Create subnetwork net_1 with B and output forwarding
        net_1 = Network(
            name="net_1",
            inports=[],
            outports=["out"],
            blocks={"B": B},
            connections=[
                ("B", "out", "external", "out")  # B.out → net_1.out
            ]
        )

        # Create subnetwork net_2 with C and input forwarding
        net_2 = Network(
            name="net_2",
            inports=["in"],
            outports=[],
            blocks={"C": C},
            connections=[
                ("external", "in", "C", "in")  # net_2.in → C.in
            ]
        )

        # Top-level network
        net_0 = Network(
            name="net_0",
            inports=[],
            outports=[],
            blocks={"net_1": net_1, "net_2": net_2},
            connections=[
                ("net_1", "out", "net_2", "in")  # net_1.out → net_2.in
            ]
        )

        def init_fn_for_X(agent):
            for i in range(5):
                agent.send(msg=i, outport='out')

        saved_for_Y = []

        def handle_msg_for_Y(agent, msg):
            saved_for_Y.append(msg)

        # Create runnable blocks
        X = SimpleAgent('X', outports=["out"], init_fn=init_fn_for_X)
        Y = SimpleAgent('Y', handle_msg=handle_msg_for_Y)

        # Create subnetwork net_ZX with X and output forwarding
        net_ZX = Network(
            name="net_ZX",
            inports=[],
            outports=["out"],
            blocks={"X": X},
            connections=[
                ("X", "out", "external", "out")
            ]
        )

        # Create subnetwork net_ZY with Y and input forwarding
        net_ZY = Network(
            name="net_ZY",
            inports=["in"],
            outports=[],
            blocks={"Y": Y},
            connections=[
                ("external", "in", "Y", "in")
            ]
        )

        # Top-level network
        net_Z = Network(
            name="net_Z",
            inports=[],
            outports=[],
            blocks={"net_ZX": net_ZX, "net_ZY": net_ZY},
            connections=[
                ("net_ZX", "out", "net_ZY", "in")  # net_1.out → net_2.in
            ]
        )

        # Top-level network
        net_TOP = Network(
            name="net_TOP",
            inports=[],
            outports=[],
            blocks={"net_Z": net_Z, "net_0": net_0},
            connections=[]  # No connections in the top-level network
        )

        s = Distripy(net_TOP)
        s.compile()
        s.run()
        self.assertEqual(saved_for_C, [0, 1, 2])
        self.assertEqual(saved_for_Y, [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
