## 🧩 1.5 Sharing Mutable Objects


## 🎯 Goal


- Understand the danger of modifying mutable objects by different agents. Later in the course we will describe methods for safe sharing of mutables.
---

## 💻 Example: problems with concurrently modifying mutables
 
```python
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
    print("msg.notes:", msg["notes"])
    # msg.notes == ['A1', 'B1']


g = network([(src, run_A), (run_A, run_B), (run_B, snk)])
g.run_network()

print("A.my_list:", a.my_list)  # A.my_list == ['A1', 'B1']
print("B.my_list:", b.my_list)  # B.my_list == ['A1', 'B1']
```
## 📍 Filtering Streams
Transform functions return a value. If the value is ```None`` then the value is not sent. This mechanism can be used to filter message streams.


## 🧠 Key Concepts
- ```None``` is not sent as a message
- Filtering streams