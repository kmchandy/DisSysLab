
from dsl.core import Agent, Network
import unittest
import pytest
pytest.importorskip(
    "openai", reason="Install with: pip install -e '.[gpt]' to run GPT tests")


class TestNetwork(unittest.TestCase):

    def test_1(self):
        '''
        Tests a simple network with a sender agent and  a receiver agent.
        The sender sends three messages (0, 1, 2) to the receiver.
        The receiver saves the messages it received in a local list, saved.
        This network is closed, i.e. it has no inports or outports to external
        blocks.
        '''

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
        '''
        Tests a simple network with a sender, receiver, and transformer agent.
        The sender sends three messages (0, 1, 2) to the receiver.
        The transformer multiplies the messages it receives by 2 and outputs result.
        The receiver saves the messages it received in a local list, saved.
        This network is closed, i.e. it has no inports or outports to external
        blocks.
        '''

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
        '''
        Tests a network with 5 agents.
        Agents sender_0 sends 0, 1, 2 on its outport "out".
        Agent sender_1 sends 0, 1, 4, 9 on its outport "out".
        Agent transformer receives messages from sender_0 on the
        transformer's inport "in_0" and receives messages from sender_1 
        on the transformer's inport "in_1". For each pair of messages.
        It waits for a message from each of its two inports and sends
        the sum of the two messages on its outport "sum" and the product
        of the two messages on its outport "prod".
        The output from outport "sum" is fed to a recorder agent receiver_0,
        and the output from outport "prod" is fed to a recorder agent receiver_1.
        '''

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

    def test_4(self):
        '''
        Tests a sender agent that sends "Hello" to a
        receiver agent. Similar to test_two_simple_agents
        and the difference is use of Agent.

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

    def test_5(self):
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

        if __name__ == "__main__":
            unittest.main()
