import unittest
from dsl.core import RunnableBlock, Network, Agent, SimpleAgent
from dsl.core import traverse_block_hierarchy, make_channels_for_connections, run


class TestFlattenNetwork(unittest.TestCase):
    def test_flatten_nested_network(self):
        def init_fn_for_B(agent):
            for i in range(3):
                agent.send("out", i)

        def run_fn_for_C(agent):
            msg = agent.recv('in')
            print(f"C received: {msg}")

        # Create runnable blocks
        B = SimpleAgent('B', outports=["out"], init_fn=init_fn_for_B)
        C = SimpleAgent('C', handle_msg=run_fn_for_C)

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
        atomic_blocks, graph_connections = traverse_block_hierarchy(net_0)
        make_channels_for_connections(atomic_blocks, graph_connections)
        run(atomic_blocks)

        # print(f'atomic_blocks: {atomic_blocks}')
        # print(f'\n \n')
        # prefix, unresolved_connections, graph_connections, atomic_blocks = flatten(
        #     net_0, prefix=[], unresolved_connections=[],
        #     graph_connections=[], atomic_blocks=atomic_blocks)

        # self.assertEqual(list(atomic_blocks.keys()),
        #                  ['net_0.net_1.B', 'net_0.net_2.C'])
        # self.assertEqual(graph_connections,
        #                  [('net_0.net_1.B', 'out', 'net_0.net_2.C', 'in')])
        # self.assertEqual(unresolved_connections, [])


class TestFlattenNetwork_2(unittest.TestCase):

    def test_flatten_nested_network_2(self):
        # Create runnable blocks
        B = RunnableBlock("B", inports=[], outports=["out"])
        C = RunnableBlock("C", inports=["in"], outports=[])

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

        # Create atomic blocks
        X = RunnableBlock("X", inports=[], outports=["out"])
        Y = RunnableBlock("Y", inports=["in"], outports=[])

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

        traverse_block_hierarchy(net_TOP)
#         print(f'\n \n')
#         prefix, unresolved_connections, graph_connections, atomic_blocks = flatten(
#             net_TOP, prefix=[], unresolved_connections=[],
#             graph_connections=[], atomic_blocks=atomic_blocks)


if __name__ == "__main__":
    unittest.main()
