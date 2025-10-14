# lessons.01_networks.mutables

from dsl import network


class AgentA:
    def __init__(self):
        self.my_list = []  # A's local state

    def run(self, msg):
        # ❌ BUG: A publishes *its local list object* into the message
        msg["notes"] = self.my_list
        msg["notes"].append("A1")  # mutate (also mutates A.my_list)
        return msg


class AgentB:
    def __init__(self):
        self.my_list = []  # B's local state

    def run(self, msg):
        # ❌ BUG: B *adopts the same object* from the message
        self.my_list = msg["notes"]   # alias, not a copy
        # mutate (also mutates A.my_list and B.my_list)
        msg["notes"].append("B1")
        return msg


a, b = AgentA(), AgentB()
def run_A(msg): return a.run(msg)
def run_B(msg): return b.run(msg)


def src():
    yield {}  # empty message to start


def snk(msg):
    print("msg.notes:", msg["notes"], " id:", id(msg["notes"]))
    print("A.my_list:", a.my_list,     " id:", id(a.my_list))
    print("B.my_list:", b.my_list,     " id:", id(b.my_list))
    # All three ids match → it's the SAME object
    #
    # msg.notes: ['A1', 'B1']
    # A.my_list: ['A1', 'B1']
    # B.my_list: ['A1', 'B1']


g = network([(src, run_A), (run_A, run_B), (run_B, snk)])
g.run_network()
