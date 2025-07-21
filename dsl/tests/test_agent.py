
import unittest
from multiprocessing import SimpleQueue
import os
from dsl.core import Agent, Network, SimpleAgent
from dsl.block_lib.stream_generators import StreamGenerator
from dsl.block_lib.stream_recorders import StreamToList, StreamToFile, StreamCopy
from dsl.block_lib.stream_transformers import StreamTransformer


class TestNetwork(unittest.TestCase):

    def test_1(self):

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
            blocks={"sender": Agent(outports=["out"], run=f,),
                    "receiver": Agent(inports=["in"], run=g)},
            connections=[
                ("sender", "out", "receiver", "in")
            ]
        )
        net.compile()
        # Run the network
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])
        print(f'test_1 passed')

    def test_2(self):

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
        net.compile()
        net.run()
        self.assertEqual(net.blocks['receiver'].saved, [0, 2, 4])
        print(f'test_2 passed')

    def test_3(self):

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
                "sender_0": Agent(outports=['out'], run=f_0),
                "sender_1": Agent(outports=['out'], run=f_1),
                "transformer": Agent(inports=['in_0', 'in_1'], outports=['sum', 'prod'], run=h),
                "receiver_0": Agent(inports=['in'], run=g),
                "receiver_1": Agent(inports=['in'], run=g),
            },
            connections=[
                ("sender_0", "out", "transformer", "in_0"),
                ("sender_1", "out", "transformer", "in_1"),
                ("transformer", "sum", "receiver_0", "in"),
                ("transformer", "prod", "receiver_1", "in"),
            ]
        )

        net.compile()
        net.run()

        self.assertEqual(net.blocks['receiver_0'].saved, [0, 2, 6])
        self.assertEqual(net.blocks['receiver_1'].saved, [0, 1, 8])
        print(f'test_3 passed')

    def test_4(self):
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
                       "output"], run=sender_run)
        receiver = Agent(name='receiver', inports=[
                         "input"], run=receiver_run)

        # Create the network with two blocks, sender and receiver
        blocks = {"sender": sender, "receiver": receiver}
        connections = [("sender", "output", "receiver", "input")]
        net = Network(name="net", blocks=blocks, connections=connections)

        # Run the network
        net.compile()
        net.run()

        # Check run
        self.assertEqual(received, ["Hello"])
        print(f'test_4 passed')

    def test_5(self):
        print(f'test_5 starting')
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
            hello_msg = self.recv("hello_port")
            received.append(hello_msg)
            world_msg = self.recv("world_port")
            received.append(world_msg)
            print(f"received = {received}")

        # Instantiate the agents.
        sender_hello_agent = Agent(
            name="sends_hello", outports=["out"], run=sender_hello_run
        )
        sender_world_agent = Agent(
            name="sends_world", outports=["out"], run=sender_world_run
        )
        receiver = Agent(name='receiver', inports=[
                         "hello_port", "world_port"], run=receiver_run)

        # Create the network
        blocks = {
            "sender_world_agent": sender_world_agent,
            "sender_hello_agent": sender_hello_agent,
            "receiver": receiver}
        connections = [
            ["sender_world_agent", "out", "receiver", "world_port"],
            ["sender_hello_agent", "out", "receiver", "hello_port"],
        ]
        net = Network(name="net", blocks=blocks, connections=connections)

        # Run the network
        net.compile()
        net.run()

        # Check that network runs correctly
        self.assertEqual(received, {'helloworld'})
        print(f'test_5 passed')

        #     def test_6(self):
        #         print(f'test_6 starting')
        #         receiver = SimpleAgent(name="Receiver", inport="in")

        #         # The invalid port 'bad_out' will trigger an error during Network construction
        #         with self.assertRaises(RuntimeError) as context:
        #             net = Network(
        #                 name="BadNet",
        #                 inports=[],
        #                 outports=[],
        #                 blocks={
        #                     "sender": SimpleAgent(name="Sender", outports=["out"]),
        #                     "receiver": receiver},
        #                 connections=[
        #                     ("sender", "bad_out", "receiver", "in")
        #                 ]
        #             )

        #         # Optional: verify error message contains helpful hints
        #         self.assertIn("bad_out", str(context.exception))
        #         self.assertIn("failed", str(context.exception))
        #         print(f'test_6 passed')

        # class Test7(unittest.TestCase):
        #     def test_stream_generator_range(self):

        #         def emit_range():
        #             for i in range(5):
        #                 yield i

        #         # Create the network
        #         net = Network(
        #             name="net",
        #             blocks={
        #                 'stream_generator_agent': StreamGenerator(
        #                     generator_fn=emit_range
        #                 ),
        #                 'receiver': StreamToList(),
        #             },
        #             connections=[
        #                 ('stream_generator_agent', 'out', 'receiver', 'in')
        #             ]
        #         )

        #         # Run the network
        #         net.compile()
        #         net.run()

        #         # Check that network runs correctly
        #         self.assertEqual(
        #             net.blocks['receiver'].saved, [0, 1, 2, 3, 4])
        #         print(f'test_7 passed')

        # class TestStreamAgentDouble(unittest.TestCase):
        #     def test_8(self):

        #         def emit_range():
        #             for i in range(7):
        #                 yield i

        #         def handle_msg(self, msg):
        #             self.send(2*msg, outport='out')

        #         # Instantiate the agents
        #         stream_generator_agent = StreamGenerator(
        #             name="range_generator",
        #             generator_fn=emit_range
        #         )
        #         checking_agent = SimpleAgent(
        #             inport='in',
        #             outports=['out'],
        #             init_fn=None,
        #             handle_msg=handle_msg
        #         )
        #         receiver = StreamToList()

        #         net = Network(
        #             name="Net",
        #             inports=[],
        #             outports=[],
        #             blocks={
        #                 "stream_generator": stream_generator_agent,
        #                 "checking_agent": checking_agent,
        #                 "receiver": receiver},
        #             connections=[
        #                 ("stream_generator", "out", "checking_agent", "in"),
        #                 ("checking_agent", "out", "receiver", "in")
        #             ]
        #         )
        #         # Run the network
        #         net.compile()
        #         net.run()
        #         # Check that network runs correctly
        #         self.assertEqual(receiver.saved, [0, 2, 4, 6, 8, 10, 12])
        #         print(f'test_8 passed')

        # class TestStreamTransformer(unittest.TestCase):

        #     def count_up_to(n):
        #         for i in range(n):
        #             yield i

        #     net = Network(
        #         name='net',
        #         blocks={
        #             'gen': StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3}),
        #             'receiver': StreamToList(),
        #         },
        #         connections=[('gen', 'out', 'receiver', 'in')]
        #     )
        #     net.compile()
        #     net.run()
        #     assert net.blocks['receiver'].saved == [0, 1, 2]

        #     def test_9(self):
        #         print(f'test_9 starting')

        #         def emit_range():
        #             for i in range(5):
        #                 yield i

        #         receiver = StreamToList()

        #         net = Network(
        #             name="double_net",
        #             blocks={
        #                 'stream_generator_agent': StreamGenerator(
        #                     generator_fn=emit_range
        #                 ),
        #                 'receiver': receiver,
        #                 'transformer': StreamTransformer(
        #                     transform_fn=lambda v: 2*v
        #                 ),
        #             },
        #             connections=[
        #                 ('stream_generator_agent', 'out', 'transformer', 'in'),
        #                 ('transformer', 'out', 'receiver', 'in')
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(receiver.saved, [0, 2, 4, 6, 8])
        #         print(f'test_9 passed')

        # class TestStreamCopy(unittest.TestCase):
        #     def test_10(self):
        #         def emit_range():
        #             for i in range(3):
        #                 yield i

        #         # Two collectors to verify both output streams receive data
        #         collector_main = StreamToList(name="main_collector")
        #         collector_watch = StreamToList(name="watch_collector")

        #         net = Network(
        #             name="copy_test_net",
        #             blocks={
        #                 "generator": StreamGenerator(
        #                     name="emitter",
        #                     generator_fn=emit_range,
        #                 ),
        #                 "copier": StreamCopy(name="stream_tee"),
        #                 "main_sink": collector_main,
        #                 "watch_sink": collector_watch,
        #             },
        #             connections=[
        #                 ("generator", "out", "copier", "in"),
        #                 ("copier", "main", "main_sink", "in"),
        #                 ("copier", "watch", "watch_sink", "in"),
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(collector_main.saved, [0, 1, 2])
        #         self.assertEqual(collector_watch.saved, [0, 1, 2])
        #         print(f'test_10 passed')

        # class TestStreamToFileCopy(unittest.TestCase):
        #     def test_11(self):
        #         print(f'test_11 starting')
        #         # Temporary log file
        #         log_file = "test_stream_log.txt"

        #         # Clean up file if exists
        #         if os.path.exists(log_file):
        #             os.remove(log_file)

        #         def emit_range():
        #             for i in range(3):
        #                 yield i

        #         net = Network(
        #             name="copy_file_net",
        #             blocks={
        #                 "generator": StreamGenerator(
        #                     name="generator", generator_fn=emit_range
        #                 ),
        #                 "logger": StreamToFile(filename=log_file),
        #                 "receiver": StreamToList(),
        #             },
        #             connections=[
        #                 ("generator", "out", "logger", "in"),
        #                 ("logger", "out", "receiver", "in"),
        #             ],
        #         )

        #         net.compile()
        #         net.run()

        #         # Check list capture
        #         self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])

        #         # Check file contents
        #         with open(log_file, "r") as f:
        #             lines = f.read().splitlines()
        #         self.assertEqual(lines, ["0", "1", "2"])

        #         # Clean up file
        #         os.remove(log_file)
        #         print(f'test_11 passed')

        # class TestSimplestAgent(unittest.TestCase):
        #     def test_12(self):
        #         print(f'test_12 starting')

        #         def f(self):
        #             self.n = 3
        #             for i in range(self.n):
        #                 self.send(msg=i, outport='out')
        #             self.send(msg='__STOP__', outport='out')

        #         def g(self):
        #             self.saved = []
        #             while True:
        #                 msg = self.recv(inport='in')
        #                 if msg == "__STOP__":
        #                     break
        #                 else:
        #                     self.saved.append(msg)

        #         net = Network(
        #             name='net',
        #             blocks={
        #                 "sender": Agent(outports=['out'], run=f),
        #                 "receiver": Agent(inports=['in'], run=g),
        #             },
        #             connections=[
        #                 ("sender", "out", "receiver", "in")
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])
        #         print(f'test_12 passed')

        #         net = Network(
        #             name='net',
        #             blocks={
        #                 "sender": Agent(outports=['out'], run=f),
        #                 "receiver": Agent(inports=['in'], run=g),
        #             },
        #             connections=[
        #                 ("sender", "out", "receiver", "in")
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(net.blocks['receiver'].saved, [0, 1, 2])
        #         print(f'test_13 passed')

        # class TestSimpleTransformerAgent(unittest.TestCase):
        #     def test_14(self):
        #         print(f'test_14 starting')

        #         def f(self):
        #             self.n = 3
        #             for i in range(self.n):
        #                 self.send(msg=i, outport='out')
        #             self.send(msg='__STOP__', outport='out')

        #         def g(self):
        #             self.saved = []
        #             while True:
        #                 msg = self.recv(inport='in')
        #                 if msg == "__STOP__":
        #                     break
        #                 else:
        #                     self.saved.append(msg)

        #         def double(self):
        #             while True:
        #                 msg = self.recv(inport='in')
        #                 if msg == "__STOP__":
        #                     self.send(msg=msg, outport='out')
        #                     break
        #                 else:
        #                     self.send(msg=2*msg, outport='out')

        #         net = Network(
        #             name="net",
        #             blocks={
        #                 "sender": Agent(outports=['out'], run=f),
        #                 "transformer": Agent(inports=['in'], outports=['out'], run=double),
        #                 "receiver": Agent(inports=['in'], run=g),
        #             },
        #             connections=[
        #                 ("sender", "out", "transformer", "in"),
        #                 ("transformer", "out", "receiver", "in"),
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(net.blocks['receiver'].saved, [0, 2, 4])
        #         print(f'test_14 passed')

        # class TestMultipleInputTransformerAgent(unittest.TestCase):
        #     def test_15(self):
        #         print(f'test_15 starting')

        #         def f_0(self):
        #             self.n = 3
        #             for i in range(self.n):
        #                 self.send(msg=i, outport='out')
        #             self.send(msg='__STOP__', outport='out')

        #         def f_1(self):
        #             self.n = 4
        #             for i in range(self.n):
        #                 self.send(msg=i*i, outport='out')
        #             self.send(msg='__STOP__', outport='out')

        #         def g(self):
        #             self.saved = []
        #             while True:
        #                 msg = self.recv(inport='in')
        #                 if msg == "__STOP__":
        #                     break
        #                 else:
        #                     self.saved.append(msg)

        #         def h(self):
        #             while True:
        #                 msg_0 = self.recv(inport='in_0')
        #                 if msg_0 == "__STOP__":
        #                     for outport in self.outports:
        #                         self.send(msg='__STOP__', outport=outport)
        #                     break
        #                 else:
        #                     msg_1 = self.recv(inport='in_1')
        #                     if msg_1 == "__STOP__":
        #                         for outport in self.outports:
        #                             self.send(msg='__STOP__', outport=outport)
        #                         break
        #                     else:
        #                         self.send(msg=msg_0 + msg_1, outport='sum')
        #                         self.send(msg=msg_0 * msg_1, outport='prod')

        #         net = Network(
        #             name="net",
        #             blocks={
        #                 "sender_0": Agent(outports=['out'], run=f_0),
        #                 "sender_1": Agent(outports=['out'], run=f_1),
        #                 "transformer": Agent(inports=['in_0', 'in_1'], outports=['sum', 'prod'], run=h),
        #                 "receiver_0": Agent(inports=['in'], run=g),
        #                 "receiver_1": Agent(inports=['in'], run=g),
        #             },
        #             connections=[
        #                 ("sender_0", "out", "transformer", "in_0"),
        #                 ("sender_1", "out", "transformer", "in_1"),
        #                 ("transformer", "sum", "receiver_0", "in"),
        #                 ("transformer", "prod", "receiver_1", "in"),
        #             ]
        #         )
        #         net.compile()
        #         net.run()
        #         self.assertEqual(net.blocks['receiver_0'].saved, [0, 2, 6])
        #         self.assertEqual(net.blocks['receiver_1'].saved, [0, 1, 8])
        #         print(f'test_15 passed')

        #     # Tests

        #     def test_16(self):
        #         print(f'test_16 starting')

        #         def count_up_to(n):
        #             for i in range(n):
        #                 yield i

        #         net = Network(
        #             name="net",
        #             blocks={
        #                 'gen': StreamGenerator(generator_fn=count_up_to, kwargs={'n': 3}),
        #                 'receiver': StreamToList(),
        #             },
        #             connections=[('gen', 'out', 'receiver', 'in')]
        #         )

        #         net.compile()
        #         net.run()

        #         self.assertEqual(net.blocks['receiver'].saved, [0, 2, 6])
        #         print(f'test_16 passed')

        if __name__ == "__main__":
            unittest.main()
