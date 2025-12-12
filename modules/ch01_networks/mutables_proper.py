# modules.ch01_networks.mutables

from dsl import network


class AgentA:
    def __init__(self):
        self.my_list = []  # A's local state

    def run(self, msg):
        # msg["notes"] is a copy of A.my_list
        msg["notes"] = list(self.my_list)
        msg["notes"].append("A1")     # modifies msg["notes"] but not A.my_list
        # Now msg["notes"] is ["A1"] and A.my_list remains []
        return msg


class AgentB:
    def __init__(self):
        self.my_list = []  # B's local state

    def run(self, msg):
        # B.my_list is a copy of msg["notes"]
        self.my_list = list(msg["notes"])
        # Now B.my_list = ["A1"]
        msg["notes"].append("B1")
        # Now msg["notes"] is ["A1", "B1"], and B.my_list remains ["A1"]
        # A.my_list is not changed
        return msg


a, b = AgentA(), AgentB()
def run_A(msg): return a.run(msg)
def run_B(msg): return b.run(msg)


def emit_empty_dict():
    # emits a single message which is an empty dict
    yield {}


def print_msg(msg):
    print("msg.notes:", msg["notes"], " id:", id(msg["notes"]))
    print("A.my_list:", a.my_list,     " id:", id(a.my_list))
    print("B.my_list:", b.my_list,     " id:", id(b.my_list))
    # All three ids match → it's the SAME object
    #
    # msg.notes: ['A1', 'B1']
    # A.my_list: ['A1', 'B1']
    # B.my_list: ['A1', 'B1']
    #


g = network([(emit_empty_dict, run_A), (run_A, run_B), (run_B, print_msg)])
g.run_network()
