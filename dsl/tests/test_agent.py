
import unittest
from multiprocessing import SimpleQueue
import os
from dsl.core import Agent, Network, SimpleAgent


class TestNetwork(unittest.TestCase):

    def test_1(self):
        print(f'starting test_1')

        def f(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')
            agent.send(msg='__STOP__', outport='out')

        def g(agent):
            agent.saved = []
            while True:
                msg = agent.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    agent.saved.append(msg)

        # Create the network. This network has no inports or outports
        # that are visible to other networks.
        net = Network(
            name="net_1",
            inports=[],
            outports=[],
            blocks={"sender": Agent(outports=["out"], run_fn=f,),
                    "receiver": Agent(inports=["in"], run_fn=g)},
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        # Run the network
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])
        print(f'passed test_1')

    def test_2(self):
        print(f'starting test_2')

        def f(agent):
            for i in range(3):
                agent.send(msg=i, outport='out')
            agent.send(msg='__STOP__', outport='out')

        def g(agent):
            agent.saved = []
            while True:
                msg = agent.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    agent.saved.append(msg)

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
            name="net_2",
            blocks={"sender": Agent(outports=["out"], run_fn=f,),
                    "receiver": Agent(inports=["in"], run_fn=g),
                    "transformer": Agent(inports=["in"], outports=["out"], run_fn=h),
                    },
            connections=[
                ("sender", "out", "transformer", "in"),
                ("transformer", "out", "receiver", "in")
            ]
        )
        # Run the network
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 2, 4])
        print(f'passed test_2')

    def test_3(self):
        print(f'starting test_3')

        def f_0(agent):
            agent.n = 3
            for i in range(agent.n):
                agent.send(msg=i, outport='out')
            agent.send(msg='__STOP__', outport='out')

        def f_1(agent):
            agent.n = 4
            for i in range(agent.n):
                agent.send(msg=i*i, outport='out')
            agent.send(msg='__STOP__', outport='out')

        def g(agent):
            agent.saved = []
            while True:
                msg = agent.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    agent.saved.append(msg)

        def h(agent):
            while True:
                msg_0 = agent.recv(inport='in_0')
                if msg_0 == "__STOP__":
                    for outport in agent.outports:
                        agent.send(msg='__STOP__', outport=outport)
                    break
                else:
                    msg_1 = agent.recv(inport='in_1')
                    if msg_1 == "__STOP__":
                        for outport in agent.outports:
                            agent.send(msg='__STOP__', outport=outport)
                        break
                    else:
                        agent.send(msg=msg_0 + msg_1, outport='sum')
                        agent.send(msg=msg_0 * msg_1, outport='prod')

        net = Network(
            name="net_3",
            blocks={
                "sender_0": Agent(outports=['out'], run_fn=f_0),
                "sender_1": Agent(outports=['out'], run_fn=f_1),
                "transformer": Agent(inports=['in_0', 'in_1'], outports=['sum', 'prod'], run_fn=h),
                "receiver_0": Agent(inports=['in'], run_fn=g),
                "receiver_1": Agent(inports=['in'], run_fn=g),
            },
            connections=[
                ("sender_0", "out", "transformer", "in_0"),
                ("sender_1", "out", "transformer", "in_1"),
                ("transformer", "sum", "receiver_0", "in"),
                ("transformer", "prod", "receiver_1", "in"),
            ]
        )

        net.run()
        self.assertEqual(net.blocks['receiver_0'].saved, [0, 2, 6])
        self.assertEqual(net.blocks['receiver_1'].saved, [0, 1, 8])
        print(f'passed test_3')


"""

    def test_two_agents(self):
        '''
        Tests a sender agent that sends "Hello" to a
        receiver agent. Similar to test_two_simple_agents
        and the difference is use of Agent and not
        SimpleAgent class.

        '''

        def sender_run(self):
            self.send(msg="Hello", outport="output")
            self.send(msg="__STOP__", outport="output")

        received = []

        def receiver_run(self):
            while True:
                msg = self.recv(inport="input")
                if msg == "__STOP__":
                    break
                received.append(msg)

        # Instantiate the agents
        sender = Agent(name="sends_hello_agent", outports=[
                       "output"], run_fn=sender_run)
        receiver = Agent(name='receiver', inports=[
                         "input"], run_fn=receiver_run)

        # Create the network with two blocks, sender and receiver
        blocks = {"sender": sender, "receiver": receiver}
        connections = [("sender", "output", "receiver", "input")]
        net = Network(name="net", blocks=blocks, connections=connections)

        # Run the network
        net.run()

        # Check run
        self.assertEqual(received, ["Hello"])
        print(f'passed test_two_agents')



    def test_merge_agent(self):
        '''
        Tests an agent that receives messages from
        two inports.

        '''

        def sender_hello_run(self):
            '''
            A message is a dict that identifies the sender and
            the message contents.

            '''
            self.send(
                msg={'sender': 'sends_hello', 'message': 'hello'},
                outport="out",
            )
            self.send(
                msg={'sender': 'sends_hello', 'message': '__STOP__'},
                outport="out",
            )

        def sender_world_run(self):
            '''
            Sends message 'world' and then message '__STOP__'

            '''
            self.send(
                msg={'sender': 'sends_world', 'message': 'world'},
                outport="out",
            )
            self.send(
                msg={'sender': 'sends_world', 'message': '__STOP__'},
                outport="out",
            )

        received = []

        def receiver_run(self):
            # received_stop_from is the set of agents that
            # sent '__STOP__' messages to this agent.
            received_stop_from = set()
            while True:
                msg = self.recv(inport="input")
                msg_contents = msg['message']
                msg_sender = msg['sender']
                if msg_contents != "__STOP__":
                    received.append(msg_contents)
                elif msg_sender not in received_stop_from:
                    # Add msg_sender to the set of agents
                    # that have sent __STOP__ messages.
                    received_stop_from.add(msg_sender)
                    if len(received_stop_from) == 2:
                        break
                else:
                    # The same sender is sending multiple stops.
                    pass

        # Instantiate the agents.
        sender_hello_agent = Agent(
            name="sends_hello", outports=["out"], run_fn=sender_hello_run
        )
        sender_world_agent = Agent(
            name="sends_world", outports=["out"], run_fn=sender_world_run
        )
        receiver = Agent(name='receiver', inports=[
                         "input"], run_fn=receiver_run)

        # Create the network
        blocks = {
            "sender_world_agent": sender_world_agent,
            "sender_hello_agent": sender_hello_agent,
            "receiver": receiver}
        connections = [
            ["sender_world_agent", "out", "receiver", "input"],
            ["sender_hello_agent", "out", "receiver", "input"],
        ]
        net = Network(name="net", blocks=blocks, connections=connections)

        # Run the network
        net.run()

        # Check that network runs correctly
        self.assertEqual(set(received), {'hello', 'world'})
        print(f'passed test_merge_agent')

    def test_network_check_validation(self):
        sender = SimpleAgent(name="Sender", outports=["out"])
        receiver = SimpleAgent(name="Receiver", inport="in")

        # The invalid port 'bad_out' will trigger an error during Network construction
        with self.assertRaises(RuntimeError) as context:
            net = Network(
                name="BadNet",
                inports=[],
                outports=[],
                blocks={
                    "sender": SimpleAgent(name="Sender", outports=["out"]),
                    "receiver": receiver},
                connections=[
                    ("sender", "bad_out", "receiver", "in")
                ]
            )

        # Optional: verify error message contains helpful hints
        self.assertIn("bad_out", str(context.exception))
        self.assertIn("failed", str(context.exception))
        print(f'passed test_network_check_validation')


class TestStreamAgents(unittest.TestCase):
    def test_stream_generator_range(self):

        def emit_range():
            for i in range(5):
                yield i

        # Create the network
        net = Network(
            name="net",
            blocks={
                'stream_generator_agent': StreamGenerator(
                    generator_fn=emit_range
                ),
                'receiver': StreamToList(),
            },
            connections=[
                ('stream_generator_agent', 'out', 'receiver', 'in')
            ]
        )

        # Run the network
        net.run()

        # Check that network runs correctly
        self.assertEqual(
            net.blocks['receiver'].saved, [0, 1, 2, 3, 4])
        print(f'passed test_stream_generator')


class TestStreamAgentDouble(unittest.TestCase):
    def test_transform_stream_doubles_values_version_2(self):
        print(f'starting test_transform_stream_doubles_values')

        def emit_range():
            for i in range(7):
                yield i

        def handle_msg(self, msg):
            self.send(2*msg, outport='out')

        # Instantiate the agents
        stream_generator_agent = StreamGenerator(
            name="range_generator",
            generator_fn=emit_range
        )
        checking_agent = SimpleAgent(
            inport='in',
            outports=['out'],
            init_fn=None,
            handle_msg=handle_msg
        )
        receiver = StreamToList()

        net = Network(
            name="Net",
            inports=[],
            outports=[],
            blocks={
                "stream_generator": stream_generator_agent,
                "checking_agent": checking_agent,
                "receiver": receiver},
            connections=[
                ("stream_generator", "out", "checking_agent", "in"),
                ("checking_agent", "out", "receiver", "in")
            ]
        )
        # Run the network
        net.run()
        # Check that network runs correctly
        self.assertEqual(receiver.saved, [0, 2, 4, 6, 8, 10, 12])
        print(f'passed test_transform_stream_doubles_values_version_2')


class TestStreamTransformer(unittest.TestCase):
    print(f'Starting TestStreamTransformer')

    def count_up_to(n):
        for i in range(n):
            yield i

    net = Network(
        blocks={
            'gen': StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3}),
            'receiver': StreamToList(),
        },
        connections=[('gen', 'out', 'receiver', 'in')]
    )

    net.run()
    assert net.blocks['receiver'].saved == [0, 1, 2]
    print(f'---------------------------')

    def test_transform_stream_doubles_values(self):
        def emit_range():
            for i in range(5):
                yield i

        receiver = StreamToList()

        net = Network(
            name="double_net",
            blocks={
                'stream_generator_agent': StreamGenerator(
                    generator_fn=emit_range
                ),
                'receiver': receiver,
                'transformer': StreamTransformer(
                    transform_fn=lambda v: 2*v
                ),
            },
            connections=[
                ('stream_generator_agent', 'out', 'transformer', 'in'),
                ('transformer', 'out', 'receiver', 'in')
            ]
        )
        net.run()
        self.assertEqual(receiver.saved, [0, 2, 4, 6, 8])
        print(f'passed test_stream_generator')


class TestStreamCopy(unittest.TestCase):
    def test_stream_copy_duplicates_messages(self):
        def emit_range():
            for i in range(3):
                yield i

        # Two collectors to verify both output streams receive data
        collector_main = StreamToList(name="main_collector")
        collector_watch = StreamToList(name="watch_collector")

        net = Network(
            name="copy_test_net",
            blocks={
                "generator": StreamGenerator(
                    name="emitter",
                    generator_fn=emit_range,
                ),
                "copier": StreamCopy(name="stream_tee"),
                "main_sink": collector_main,
                "watch_sink": collector_watch,
            },
            connections=[
                ("generator", "out", "copier", "in"),
                ("copier", "main", "main_sink", "in"),
                ("copier", "watch", "watch_sink", "in"),
            ]
        )

        net.run()
        self.assertEqual(collector_main.saved, [0, 1, 2])
        self.assertEqual(collector_watch.saved, [0, 1, 2])


class TestStreamToFileCopy(unittest.TestCase):
    def test_stream_to_file_copy(self):
        # Temporary log file
        log_file = "test_stream_log.txt"

        # Clean up file if exists
        if os.path.exists(log_file):
            os.remove(log_file)

        def emit_range():
            for i in range(3):
                yield i

        net = Network(
            name="copy_file_net",
            blocks={
                "generator": StreamGenerator(
                    name="generator", generator_fn=emit_range
                ),
                "logger": StreamToFileCopy(filepath=log_file),
                "receiver": StreamToList(),
            },
            connections=[
                ("generator", "out", "logger", "in"),
                ("logger", "out", "receiver", "in"),
            ],
        )

        net.run()

        # Check list capture
        self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])

        # Check file contents
        with open(log_file, "r") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines, ["0", "1", "2"])

        # Clean up file
        os.remove(log_file)

        print(f'passed TestStreamToFileCopy')


class TestSimplestAgent(unittest.TestCase):
    def test_simplest_agent(self):
        def f(self):
            self.n = 3
            for i in range(self.n):
                self.send(msg=i, outport='out')
            self.send(msg='__STOP__', outport='out')

        def g(self):
            self.saved = []
            while True:
                msg = self.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    self.saved.append(msg)

        net = Network(
            blocks={
                "sender": Agent(outports=['out'], run_fn=f),
                "receiver": Agent(inports=['in'], run_fn=g),
            },
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])

        net = Network(
            blocks={
                "sender": Agent(outports=['out'], run_fn=f),
                "receiver": Agent(inports=['in'], run_fn=g),
            },
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])
        print(f'passed TestSimplestAgent')


class TestSimpleTransformerAgent(unittest.TestCase):
    def test_simple_transformer_agent(self):

        def f(self):
            self.n = 3
            for i in range(self.n):
                self.send(msg=i, outport='out')
            self.send(msg='__STOP__', outport='out')

        def g(self):
            self.saved = []
            while True:
                msg = self.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    self.saved.append(msg)

        def double(self):
            while True:
                msg = self.recv(inport='in')
                if msg == "__STOP__":
                    self.send(msg=msg, outport='out')
                    break
                else:
                    self.send(msg=2*msg, outport='out')

        net = Network(
            blocks={
                "sender": Agent(outports=['out'], run_fn=f),
                "transformer": Agent(inports=['in'], outports=['out'], run_fn=double),
                "receiver": Agent(inports=['in'], run_fn=g),
            },
            connections=[
                ("sender", "out", "transformer", "in"),
                ("transformer", "out", "receiver", "in"),
            ]
        )

        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 2, 4])
        print(f'passed TestSimpleTransformerAgent')


class TestMultipleInputTransformerAgent(unittest.TestCase):
    def test_simple_transformer_agent(self):

        def f_0(self):
            self.n = 3
            for i in range(self.n):
                self.send(msg=i, outport='out')
            self.send(msg='__STOP__', outport='out')

        def f_1(self):
            self.n = 4
            for i in range(self.n):
                self.send(msg=i*i, outport='out')
            self.send(msg='__STOP__', outport='out')

        def g(self):
            self.saved = []
            while True:
                msg = self.recv(inport='in')
                if msg == "__STOP__":
                    break
                else:
                    self.saved.append(msg)

        def h(self):
            while True:
                msg_0 = self.recv(inport='in_0')
                if msg_0 == "__STOP__":
                    for outport in self.outports:
                        self.send(msg='__STOP__', outport=outport)
                    break
                else:
                    msg_1 = self.recv(inport='in_1')
                    if msg_1 == "__STOP__":
                        for outport in self.outports:
                            self.send(msg='__STOP__', outport=outport)
                        break
                    else:
                        self.send(msg=msg_0 + msg_1, outport='sum')
                        self.send(msg=msg_0 * msg_1, outport='prod')

        net = Network(
            blocks={
                "sender_0": Agent(outports=['out'], run_fn=f_0),
                "sender_1": Agent(outports=['out'], run_fn=f_1),
                "transformer": Agent(inports=['in_0', 'in_1'], outports=['sum', 'prod'], run_fn=h),
                "receiver_0": Agent(inports=['in'], run_fn=g),
                "receiver_1": Agent(inports=['in'], run_fn=g),
            },
            connections=[
                ("sender_0", "out", "transformer", "in_0"),
                ("sender_1", "out", "transformer", "in_1"),
                ("transformer", "sum", "receiver_0", "in"),
                ("transformer", "prod", "receiver_1", "in"),
            ]
        )

        net.run()
        self.assertEqual(net.blocks['receiver_0'].saved, [0, 2, 6])
        self.assertEqual(net.blocks['receiver_1'].saved, [0, 1, 8])
        print(f'passed TestMultipleInputTransformerAgent')

"""
if __name__ == "__main__":
    unittest.main()
