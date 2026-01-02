<!-- modules.ch01_networks.README4.md -->
## 🧩 1.4  Pattern: Enrich Dictionary Messages at Nodes


## 🎯 Goal


- Data transformers use dictionaries (```dict```) to enrich messages as they flow through a network.
---

## 💻 Example network: transformers enrich dict messages (add fields)

```python

# Messages in this example are dicts

     +-----------+
     | from_list | source of dict {'text': item}
     +-----------+
          |
          | example msg: {'text': 'hello'}
          v
     +-----------+
     |  exclaim  | add field 'exclaim' to msg
     +-----------+
          |
          | example: {'text': 'hello', 'exclaim': 'hello!'}
          v
     +-----------+
     | uppercase |   add field 'uppercase' to msg
     +-----------+
          |
          | example: {'text': 'hello', 'exclaim': 'hello!', 'uppercase': 'HELLO'}
          v
     +-----------+
     | to_results|   print msg
     |           |   example: {'text': 'hello', 'exclaim': 'hello!', 
     |           |             'uppercase': 'HELLO'}
     +-----------+           

```

## 💻 dsl program
```
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
We often use messages that are dicts. A transformer may add fields to the dict as it processes the message.  We will see that this pattern is especially useful when the data transformers are AI agents.


## 🧠 Key Concepts
- A useful pattern is to have messages that are dicts and where agents add fields to the dicts.

## 👉 Next
Look at an example
[example of a network with fanout and fanin](./README_5.md)
