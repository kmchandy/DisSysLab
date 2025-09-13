# 🧩 Lesson 1 Networks, blocks and connections


## 🎯 Goal


- Learn how to build a distributed application by creating **blocks** and connecting them to form a **network**.
---

## 📍 Example

We’ll create a **three-block network**:

1. **Source** – generate a stream of messages.
2. **Transform** – receive a message stream and output a transformation of the stream.
3. **Sink** – store or display a message stream. 

**Visual:** `[ Source ] → [ Transform ] → [ Sink ]`

---

## ⚙️ How It Works

- **🔲 Blocks**  
  - A block has sets of input  and output ports called **inports** and **outports**, respectively
  - A block executes a function that receives messages from its inports and sends messages through its outports.

- **🔗 Connections**  
  - A connection connects a block’s **output port** to a block’s **input port**. 


**Blocks in this example:**
- block name: **"source"**, 
  - execution: **FromList["hello", "world"]** – Generate a stream consisting of message "hello" followed by message "world". The stream is sent on an outport "out".
- block name: **"upper_case"**, 
  - execution: **Uppercase** – Receives a stream of messages on inport "in" and sends the uppercase of the messages that it receives on outport "out".
- block name: **"sink"**, 
  - execution: **ToList** – Receives a stream of messages on inport "in" and stores the stream that it receives in a list.

Block types with multiple inports and outports, and network structures that are not linear, are introduced later. 



---

## 💻 Code Example
 
```
# lessons.01_networks_blocks_connections.basic_network.py

from dsl.kit import Network, FromList, Uppercase, ToList


def basic_network():
    results = []  # Holds results sent to sink

    net = Network(
        blocks={
            "source": FromList(['hello', 'world']),
            "upper_case": Uppercase(),
            "sink": ToList(results),
        },
        connections=[
            ("source", "out", "upper_case", "in"),
            ("upper_case", "out", "sink", "in"),
        ],
    )

    net.compile_and_run()
    assert results == ['HELLO', 'WORLD']


if __name__ == "__main__":
    basic_network()
```

### ▶️ Run It
```
python -m lessons.01_networks_blocks_connections.basic_network
```



## 🧠 Key Takeaways

- **network = blocks + connections**  
- **blocks**: each block executes a function that *processes messages*
- **connections**:  specify how *messages flow* from block to block.

### To do X, use function Y

- **Source** To generate a stream from a list or a file,.. use functions beginning with "From" such as `FromList([...])`, `FromFile(..)`
- **Transform** To receive a stream and output a computation of the stream use functions such as `Uppercase()`, `AddSentiment`, `ExtractEntities`
- **Sink** To record a stream to the console, or a list, or file use functions beginning with "To" such as `ToConsole()`, `ToList()`, `ToFile`
  
> See `dsl/kit/README_HowTo.md`.

---

### 🚀 Coming Up

Create a network that receives movie reviews, gives each movie a score by analyzing its review, and outputs both the review and its score.

👉 [**Next up: Chapter 2. Messages as Dictionaries.**](../02_msg_as_dict/README.md)
