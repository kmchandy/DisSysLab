## 🧩 1.6 Sharing Mutable Objects


## 🎯 Goal


- Understand the danger of multiple agents concurrently modifying mutable objects. Later in the course we will describe methods for safe sharing of mutables.
---

## 💻 Example: Don't modify mutables concurrently
 
```python

     +------------------+
     | emit_empty_dict  |
     +------------------+
            |
            |  <- msg is empty dict
            v
     +------------------+
     |      run_A       |
     +------------------+
            |
            |   adds msg["notes"]
            v
     +------------------+
     |      run_B       |
     +------------------+
            |
            | concurrently modifies msg["notes"]
            v  
     +------------------+
     |    print_msg     |
     +------------------+
```

## 💻 dsl program
```
# modules.ch01_networks.mutables

from dsl import network


class AgentA:
    def __init__(self):
        self.my_list = []  # A's local state

    def run(self, msg):
        # ❌ BUG: A publishes *its local list object* into the message
        msg["notes"] = self.my_list   # alias, not a copy
        msg["notes"].append("A1")     # modifies both msg["notes"] and A.my_list
        # Now msg["notes"] is ["A1"] and A.my_list is also ["A1"]
        return msg


class AgentB:
    def __init__(self):
        self.my_list = []  # B's local state

    def run(self, msg):
        # ❌ BUG: B *aliases the same object* from the message
        self.my_list = msg["notes"]   # alias, not a copy
        # Now B.my_list = ["A1"]
        msg["notes"].append("B1")
        # Now msg["notes"] is ["A1", "B1"], and B.my_list is also ["A1", "B1"]
        # A.my_list is also ["A1", "B1"]
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


g = network([(emit_empty_dict, run_A), (run_A, run_B), (run_B, print_msg)])
g.run_network()
```
## 📍 Concurrent Modification of Mutables
Some applications require mutable objects, such as files, to be shared by multiple agents. In such applications the operating system (or supervising program) ensures that (1) at most one agent accesses the object at a time and (2) all agents that require access to the object get access to it eventually. We discuss sharing mutable agents later. Now let's look at problems that arise when mutable objects are modified concurrently.

In this example, agent ```a``` appends "A1" to ```msg['notes']``` and takes no other action. So you may think that ```a.my_list``` is either ```[]``` or ```['A1']```. But when the program terminates ```a.my_list = ['A1', 'B1']``` because when agent ```b``` modifies ```msg['notes']``` it also modifies ```a.my_list```.

You can run the example from the DisSysLab directory by executing:

```
python -m modules.ch01_networks.mutables

```

## 📍 Safe Use of Data by Multiple Agents
- ***Enrich dict messages***. As you saw in the previous module, you can use dicts and fields to the dict without modifying existing fields.
  
- If you want to use the same field of the dict -- rather than add a field --- then use a **copy**: ```msg["notes"] = list(self.my_list)```. This makes ```msg["notes"]``` a copy of ```self.my_list```, and so modifying ```msg["notes"]``` does not modify ```self.my_list```.
  
- Likewise read a **copy** of a message: ```self.my_list = list(msg["notes"])```.

## 🧠 Key Concepts
- Beware of aliasing with mutables passed through messages. Use copies of data to prevent multiple agents modifying the same data concurrently as in the following modification of agents A and B.
  
```python
class AgentA:
    def __init__(self):
        self.my_list = []  # A's local state

    def run(self, msg):
        msg["notes"] = list(self.my_list)   # msg["notes"] is a copy of A.my_list
        msg["notes"].append("A1")     # modifies msg["notes"] but not A.my_list
        # Now msg["notes"] is ["A1"] and A.my_list remains []
        return msg

class AgentB:
    def __init__(self):
        self.my_list = []  # B's local state

    def run(self, msg):
        self.my_list = list(msg["notes"])   # B.my_list is a copy of msg["notes"]
        # Now B.my_list = ["A1"]
        msg["notes"].append("B1")
        # Now msg["notes"] is ["A1", "B1"], and B.my_list remains ["A1"]
        # A.my_list is not changed
        return msg

```

You can run the corrected example from the DisSysLab directory by executing:

```
python -m modules.ch01_networks.mutables_proper

```
- 
## 👉 Next

[Explore different types of sources](../ch02_sources//README_1.md).
