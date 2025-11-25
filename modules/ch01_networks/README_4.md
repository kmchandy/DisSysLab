## 🧩 1.4  Pattern: Enrich Dictionary Messages at Nodes


## 🎯 Goal


- Use dictionaries (```dict```) to enrich messages as they flow through a network.
---

## 💻 Example of enriching messages (adding fields)

```python

# Messages in this example are dicts

     +-----------+
     | from_list |
     +-----------+
          |
          v
     +-----------+
     |  exclaim  |
     +-----------+
          |
          v
     +-----------+
     | uppercase |
     +-----------+
          |
          v
     +-----------+
     | to_results|
     +-----------+


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
## 📍 Enriching Dictionary Messages
A common pattern is to represent a message as a dict and have nodes add fields as they process it. This becomes especially useful with AI agents:

Example: an agent that extracts topics from the natural language content field of a dict message adds the field ```msg["topics"] = [...]``` to the dict.

Then an agent that determines the sentiment of the message content adds the field ```msg["sentiment"] = ...```.


## 🧠 Key Concepts
- Messages as dicts make enrichment easy: read → compute → attach → pass on.

## 👉 Next
Look at an example
[example of a network with fanout and fanin](./README_5.md)
