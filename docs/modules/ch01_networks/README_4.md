## 🧩 1.4  Pattern: Enrich Messages at Nodes


## 🎯 Goal


- Using dictionaries (```dict```) to enrich messages as they flow through a network.
---

## 💻 Example of enriching messages (adding fields)

```python
# modules.ch01_networks.simple_dict

from dsl import network

list_of_words = ['hello', 'world', 'python']


def from_list(items=list_of_words):
    for item in items:
        yield {'text': item}


def exclaim(msg):
    msg['exclaim'] = msg.get('text', '') + '!'
    return msg


def uppercase(msg):
    msg['uppercase'] = msg.get('text', '').upper()
    return msg


results = []
def to_results(v): results.append(v)


# Define the network.
g = network([(from_list, exclaim), (exclaim, uppercase),
            (uppercase, to_results)])
g.run_network()

assert results == [
    {'text': 'hello', 'exclaim': 'hello!', 'uppercase': 'HELLO'},
    {'text': 'world', 'exclaim': 'world!', 'uppercase': 'WORLD'},
    {'text': 'python', 'exclaim': 'python!', 'uppercase': 'PYTHON'}
]
```
## 📍 Enriching Messages
A common pattern is to represent a message as a dict and have nodes add fields as they process it. This becomes especially useful with AI agents:

Example: a topic-extractor adds ```msg["topics"] = [...]```.

Then a sentiment step adds ```msg["sentiment"] = -1 | 0 | 1```.


## 🧠 Key Concepts
- Messages as dicts make enrichment easy: read → compute → attach → pass on.

## 👉 Next
[Agents should not concurrently modify mutable objects](./README_5.md).  

Later in the course we will describe methods by which agents can share mutable objects. These methods ensure that (1) at most one agent reads or writes a mutable object at a time and (2) all agents that are waiting to read or write a mutable object gets to do so eventually.