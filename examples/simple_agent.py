from dsl.core import Agent, Network


class Sender(Agent):
    def __init__(self, seq, outports=["out"]):
        super().__init__()
        self.outports = outports
        self.seq = seq

    def run(self):
        for msg in self.seq:
            self.send(msg, "out")
            if msg == "__STOP__":
                break


class Receiver(Agent):
    def __init__(self, inports=["in"]):
        super().__init__()
        self.inports = inports

    def run(self):
        while True:
            msg = self.recv("in")
            print(f"Received: {msg}")
            if msg == "__STOP__":
                break


class Uppercase(Agent):
    def __init__(self, inports=["in"], outports=["out"]):
        super().__init__()
        self.inports = inports
        self.outports = outports

    def run(self):
        while True:
            msg = self.recv("in")
            if msg == "__STOP__":
                self.send(msg, "out")
                break
            upper_msg = msg.upper()
            self.send(upper_msg, "out")


net = Network(
    blocks={"src": Sender(seq=["hello", "world", "__STOP__"]),
            "uppercase": Uppercase(),
            "snk": Receiver()
            },
    connections=[("src", "out", "uppercase", "in"),
                 ("uppercase", "out", "snk", "in")]
)
net.compile_and_run()
