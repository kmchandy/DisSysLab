# 🔀 Lesson 3 Fan-Out Blocks

### 🎯 Goal
Build networks using **fan-out** (one input, multiple outputs) blocks  

---

## 📍 What We’ll Build

### Example 1


### Example 2
A very simple network that splits a stream of movie reviews based on whether the reviews were positive or negative, and then modifies the positive and negative reviews in different ways, and finally merges all reviews.

- **Generator** → emits dicts with a `"review"` field.  
- **Split** → routes each review to `"pos"` or `"neg"`.  
- **Positive branch** → adds `"!!!"` and writes into `"positive"`.  
- **Negative branch** → uppercases text and writes into `"negative"`.  
- **Merge** → joins both branches back into one stream.  
- **Recorder** → saves merged dicts.

**Visual:**  

`

                   ┌────────────┐
                   │  Generator │
                   │ {"review"} │
                   └──────┬─────┘
                          │
                      ┌───▼───┐
                      │ Split │  (routes "pos" or "neg")
                      └─┬───┬─┘
                 pos ──┘   └── neg
                       │       │
             ┌─────────▼─-┐   ┌─▼─────────-┐
             │ pos_exclaim│   │  neg_upper │
             │  + "!!!"   │   │  upper()   │
             └──────┬─────┘   └────┬───────┘
                    │              │
                    └──────┬───────┘
                       ┌--─▼─--┐
                       │ Merge │
                       └─-----─┘
                           │
                    ┌──────▼──────┐
                    │   Recorder  │
                    └─────────────┘
`


---

## 💻 Code Example

**📊 Diagram of blocks and connections:**  
![Fan-In Fan-Out Network](diagram_1.svg)

```python
# dsl/examples/ch03_fanin_fanout/review_split_merge.py

from dsl.core import Network
from dsl.block_lib.generators import GenerateFromList
from dsl.block_lib.transformers import TransformerFunction
from dsl.block_lib.recorders import RecordToList
from dsl.block_lib.fanout import Split
from dsl.block_lib.fanin import MergeAsynch

# --- Split function: classify review sentiment ---
def classify_sentiment(msg: dict) -> str:
    text = msg["review"].lower()
    if "good" in text or "great" in text:
        return "pos"
    else:
        return "neg"

# --- Transformer functions ---
def add_exclamations(x: str) -> str:
    return x + "!!!"

def to_upper(x: str) -> str:
    return x.upper()

results = []

net = Network(
    blocks={
        # Generator emits dicts: {"review": "..."}
        "gen": GenerateFromList(
            items=["Great movie", "Terrible acting", "Good plot", "Bad ending"],
            key="review"
        ),
        "split": Split(split_function=classify_sentiment,
                       outports=["pos", "neg"]),
        "pos_exclaim": TransformerFunction(
            func=add_exclamations,
            input_key="review",
            output_key="positive"
        ),
        "neg_upper": TransformerFunction(
            func=to_upper,
            input_key="review",
            output_key="negative"
        ),
        "merge": MergeAsynch(inports=["pos", "neg"]),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "split", "in"),
        ("split", "pos", "pos_exclaim", "in"),
        ("split", "neg", "neg_upper", "in"),
        ("pos_exclaim", "out", "merge", "pos"),
        ("neg_upper", "out", "merge", "neg"),
        ("merge", "out", "rec", "in"),
    ]
)

net.compile_and_run()
print(results)
```

## ▶️ Run It

```
python3 -m dsl.examples.ch03_fanin_fanout.review_split_merge
```

## ✅ Output

```
[
  {"review": "Great movie", "positive": "Great movie!!!"},
  {"review": "Terrible acting", "negative": "TERRIBLE ACTING"},
  {"review": "Good plot", "positive": "Good plot!!!"},
  {"review": "Bad ending", "negative": "BAD ENDING"}
]
```

## 🧠 Key Takeaways

- **You can build arbitrary networks** with generators, transformers, recorders, fanin and fanout blocks.

### 🚀 Coming Up

You’ve learned about arbitrary networks of blocks that process messages and connections that route messages between blocks.
What if the blocks were AI agents? 

👉 **Next up: [Chapter 4 — GPT Blocks.](../ch04_GPT/README.md)**