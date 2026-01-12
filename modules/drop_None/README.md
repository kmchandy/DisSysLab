<!-- modules.drop_None.README.md -->

## 🧩 1.3 Filtering Message Streams


## 🎯 Goal


  Data transformer drops messages in streams by returning ```None```.
---

## 💻 Example network: dropping messages
 
```python

      +----------------+
      |   from_list    | source of words
      +----------------+
               |
               v
      +----------------+
      |      drop      | drop some words
      +----------------+
               |
               v
      +----------------+
      |   to_results   | print results
      +----------------+
```

## 💻 dsl program
```
# modules.ch01_networks.simple_filter

from dsl import network

# Define functions.

list_of_words = ['t', 'hello', 'world', 'python', 'philosophy', 'is', 'fun']


def from_list(items=list_of_words):
    for item in items:
        yield item


def drop(v, min_length=2, max_length=8):
    return v if min_length <= len(v) <= max_length else None


results = []
def to_results(v): results.append(v)


# Define the network.
g = network([(from_list, drop), (drop, to_results)])
g.run_network()

print(results)
assert results == ['hello', 'world', 'python', 'is', 'fun']
```
## 📍 Filtering Streams
Transform functions return a value. If the value is ```None`` then the value is not sent. This mechanism can be used to filter message streams.


## 🧠 Key Concepts
- ```None``` is not sent as a message
- Filtering streams

## 👉 Next
[Agents add fields to messages](./README_4.md) and thus enrich messages as they flow through the network.