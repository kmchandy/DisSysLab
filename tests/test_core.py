
import unittest
from multiprocessing import SimpleQueue
import os
from dsl.core import Block, Agent, Network, SimpleAgent, StreamSource
from dsl.core import StreamTransformer, StreamToList, StreamToFile
from dsl.core import StreamCopy, StreamToFileCopy
from typing import Optional, List, Callable, Dict, Tuple, Any


class TestNetwork(unittest.TestCase):

    def test_two_simple_agents(self):
        '''
        Tests a sender agent that sends "Hello" to a receiver
        that saves the stream to a stream.

        '''

        def init_fn(self):
            '''
            The sender sends message "hello" and then 
            "__STOP__"

            '''
            self.send(msg="hello", outport="out")
            self.send(msg="__STOP__", outport="out")

        # The agent, receiver, saves the stream that arrives at its
        # input port 'in' to a list, receiver.saved.
        receiver = StreamToList()

        # Create the network. This network has no inports or outports
        # that are visible to other networks.
        net = Network(
            name="Net",
            inports=[],
            outports=[],
            blocks={"sender": SimpleAgent(
                name="sender", outports=["out"], init_fn=init_fn,),
                "receiver": receiver},
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        # Run the network
        net.run()
        self.assertEqual(receiver.saved, ["hello"])
        print(f'passed test_two_simple_agents')

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
    def test_stream_source_range(self):

        def emit_range(agent):
            for i in range(5):
                agent.send(i, "out")
            agent.send("__STOP__", "out")

        # Create the network
        net = Network(
            name="net",
            blocks={
                'stream_source_agent': StreamSource(
                    stream_source_fn=emit_range
                ),
                'receiver': StreamToList(),
            },
            connections=[
                ('stream_source_agent', 'out', 'receiver', 'in')
            ]
        )

        # Run the network
        net.run()

        # Check that network runs correctly
        self.assertEqual(
            net.blocks['receiver'].saved, [0, 1, 2, 3, 4])
        print(f'passed test_stream_source')


class TestStreamAgentDouble(unittest.TestCase):
    def test_transform_stream_doubles_values_version_2(self):
        print(f'starting test_transform_stream_doubles_values')

        def emit_range(agent):
            for i in range(7):
                agent.send(i, 'out')
            agent.send('__STOP__', 'out')

        def handle_msg(self, msg):
            self.send(2*msg, outport='out')

        # Instantiate the agents
        stream_source_agent = StreamSource(
            name="range_source",
            stream_source_fn=emit_range
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
                "stream_source": stream_source_agent,
                "checking_agent": checking_agent,
                "receiver": receiver},
            connections=[
                ("stream_source", "out", "checking_agent", "in"),
                ("checking_agent", "out", "receiver", "in")
            ]
        )
        # Run the network
        net.run()
        # Check that network runs correctly
        self.assertEqual(receiver.saved, [0, 2, 4, 6, 8, 10, 12])
        print(f'----------------------------------------------')
        print(f'passed test_transform_stream_doubles_values_version_2')


class TestStreamTransformer(unittest.TestCase):
    print(f'Starting TestStreamTransformer')

    def test_transform_stream_doubles_values(self):
        def emit_range(agent):
            for i in range(5):
                agent.send(i, "out")
            agent.send("__STOP__", "out")

        receiver = StreamToList()

        net = Network(
            name="double_net",
            blocks={
                'stream_source_agent': StreamSource(
                    stream_source_fn=emit_range
                ),
                'receiver': receiver,
                'transformer': StreamTransformer(
                    transform_fn=lambda v: 2*v
                ),
            },
            connections=[
                ('stream_source_agent', 'out', 'transformer', 'in'),
                ('transformer', 'out', 'receiver', 'in')
            ]
        )
        net.run()
        self.assertEqual(receiver.saved, [0, 2, 4, 6, 8])
        print(f'passed test_stream_source')


class TestStreamCopy(unittest.TestCase):
    def test_stream_copy_duplicates_messages(self):
        def emit_range(agent):
            for i in range(3):
                agent.send(i, "out")
            agent.send("__STOP__", "out")

        # Two collectors to verify both output streams receive data
        collector_main = StreamToList(name="main_collector")
        collector_watch = StreamToList(name="watch_collector")

        net = Network(
            name="copy_test_net",
            blocks={
                "source": StreamSource(
                    name="emitter",
                    stream_source_fn=emit_range
                ),
                "copier": StreamCopy(name="stream_tee"),
                "main_sink": collector_main,
                "watch_sink": collector_watch,
            },
            connections=[
                ("source", "out", "copier", "in"),
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

        def emit_range(agent):
            for i in range(3):
                agent.send(i, "out")
            agent.send("__STOP__", "out")

        net = Network(
            name="copy_file_net",
            blocks={
                "source": StreamSource(
                    name="source", stream_source_fn=emit_range
                ),
                "logger": StreamToFileCopy(filepath=log_file),
                "receiver": StreamToList(),
            },
            connections=[
                ("source", "out", "logger", "in"),
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


if __name__ == "__main__":
    unittest.main()
