# 🧩 Step 1 — Networks = Blocks + Connections

In **DisSysLab**, a distributed application is built by **creating blocks** and **connecting them** into a network.

A **block**:
- Has zero or more **input ports**
- Has zero or more **output ports**
- Runs a function or prompt to **generate**, **transform**, or **record** messages

A **network** is just:
1. A set of **blocks**
2. A set of **connections** between block ports

---

## 🔧 Example: Generator → Transformer → Recorder

We will:
1. **Generate**: A list of short text strings.
2. **Transform**: Classify each string’s sentiment using GPT.
3. **Record**: Save results in a Python list.

---

**Diagram:**
[ Generator ] → [ Sentiment Classifier ] → [ Recorder ]

![Example Pipeline](/docs/images/simple_network.svg)

---

## 📜 Code

```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_recorders import RecordToList

results = []

net = Network(
    blocks={
        "gen": generate(
            [
                "I love sunny days",
                "I hate traffic jams",
                "This pizza is amazing",
            ],
            key="text",
        ),
        "sentiment": SentimentClassifierWithGPT(input_key="text", output_key="sentiment"),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "sentiment", "in"),
        ("sentiment", "out", "rec", "in"),
    ],
)

net.compile_and_run()


print("Final Results:")
for item in results:
    print(item)
```

## ▶️ Run the Example

python step1_pipeline.py
You should see each input string paired with its sentiment.

## 🧠 Key Points
Blocks do the work (generate, transform, record).

Connections define how messages flow between blocks.

This pattern — blocks + connections — is the foundation of every DisSysLab application.

---

## **3. `step1_pipeline.py`**

```python
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_recorders import RecordToList

results = []

net = Network(
    blocks={
        "gen": generate(
            [
                "I love sunny days",
                "I hate traffic jams",
                "This pizza is amazing",
            ],
            key="text",
        ),
        "sentiment": SentimentClassifierWithGPT(input_key="text", output_key="sentiment"),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "sentiment", "in"),
        ("sentiment", "out", "rec", "in"),
    ],
)

net.compile_and_run()

print("Final Results:")
for item in results:
    print(item)
```