## 🧩 1.5 Sharing Mutable Objects


## 🎯 Goal


- Understand the danger of multiple agents concurrently modifying mutable objects. Later in the course we will describe methods for safe sharing of mutables.
---

## 💻 Example: Don't modify mutables concurrently
 
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
```
## 📍 Concurrent Modification of Mutables
Some applications require mutable objects, such as files, to be shared by multiple agents. In such applications the operating system (or supervising program) ensures that (1) at most one agent accesses the object at a time and (2) all agents that require access to the object get access to it eventually. We discuss sharing mutable agents later. Now let's look at problems that arise when mutable objects are modified concurrently.

In this example, agent ```a``` appends "A1" to ```msg['notes']``` and takes no other action. So you may think that ```a.my_list``` is either ```[]``` or ```['A1']```. But when the program terminates ```a.my_list = ['A1', 'B1']``` because when agent ```b``` modifies ```msg['notes']``` it also modifies ```a.my_list```.

## 📍 Safe Use of Data by Multiple Agents
- Send a **copy**: ```msg["notes"] = list(self.my_list)```. This makes ```msg["notes"]``` a copy of ```self.my_list```, and so modifying ```msg["notes"]``` does not modify ```self.my_list```.
  
- Read a **copy** of a message: ```self.my_list = list(msg["notes"])```.
  
- Note that as you saw in the previous lesson: You can enrich a message, by adding fields to the message without otherwise modifying the message.

## 🧠 Key Concepts
- Beware of aliasing with mutables passed through messages.

- If you need independent state, copy before mutate (or use immutables).