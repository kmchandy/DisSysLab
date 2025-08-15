# 🔀 Chapter 3 — Fan-In and Fan-Out

### 🎯 Goal
Learn how to build **non-pipeline networks** using **fan-out** (one input, multiple outputs) and **fan-in** (multiple inputs, one output).  
This lets us branch and re-combine streams, enabling richer applications.

---

## 📍 What We’ll Build

We’ll create a **sentiment-split network**:

- **Generator** → emits dicts with a `"review"` field.  
- **Split** → routes each review to `"pos"` or `"neg"`.  
- **Positive branch** → adds `"!!!"` and writes into `"positive"`.  
- **Negative branch** → uppercases text and writes into `"negative"`.  
- **Merge** → joins both branches back into one stream.  
- **Recorder** → saves merged dicts.

**Visual:**  
`[ Generator ] → [ Split ] → (Positive branch / Negative branch) → [ Merge ] → [ Recorder ]`

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

- **Fan-out** (Split): one stream branches into multiple paths.  
- **Fan-in** (Merge): multiple paths converge back into one stream.  
- Each branch can **add its own fields** (like `"positive"` or `"negative"`) while preserving the original message.  
- Networks can be **richer than simple pipelines** — you can fork, transform, and join streams flexibly.

