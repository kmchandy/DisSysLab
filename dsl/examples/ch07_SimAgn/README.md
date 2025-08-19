# 🧩 Chapter 7 — Simple Agents

### 🎯 Goal
Learn how to use the SimpleAgent class to as the parent class of many classes including generators, transformers, and recorders. Also use the examples on this page to review concepts of similarities between documents.

---

## 📍 What We’ll Build

We’ll create a **three-block network**:

1. **Generator** – produces a list of short text strings.  
2. **SimpleAgent** – initialied with a reference string; then receives messages which are strings and compares the messages with the reference string and outputs a similarity score.
3. **Recorder** – saves the results in a Python list.

**Visual:** `[ Generator ] → [ SimpleAgent ] → [ Recorder ]`

We will build two versions of the SimpleAgent: the first uses a simple measure of similarity and the second illustrates different similarity measures.
---

## ⚙️ How It Works

- **🔲 SimpleAgent**  
  - A SimpleAgent has a single inport -- called "in" by convention -- and has an arbitrary number of outports.
  - A SimpleAgent is specified by two functions: **init_fn** and **handle_msg**
  - When a SimpleAgent object is instantiated its **init_fn** is executed. This function sets up initial values of the object's parameters and may also send messages.
  - A SimpleAgent object waits to receive messages on its inport. It applies the **handle_msg** function to the message it receives. The handle_msg function may send messages. If **handle_msg** is not specified or is Null then the object terminates after executing init_fn.


---

## 💻 Code Example

 
```python
from dsl.core import SimpleAgent
# In this example the SimpleAgent object has a single outport called "out".
# A SimpleAgent may have any number (including 0) of outports with arbitrary names.


def make_similarity_agent_simple(reference_sentence: str, name: str = "SimilarityAgent(Simple)"):
    ref_words = set(str(reference_sentence).lower().split())

    def init_fn(agent):
      # This function initializes parameters of the object, setting up its initial state.
      agent.state = {"ref": ref_words}
      print(f"[{name}] ref='{reference_sentence}' (overlap count)")

    def handle_msg(agent, msg, inport=None):
      # This function is applied to each message that the agent receives.
      toks = set(str(msg).lower().split())
      # Compute the overlap of msg with the reference
      overlap = len(agent.state["ref"] & toks)
      # Send msg and overlap on the outport "out"
      agent.send({"input": str(msg), "overlap": overlap}, outport="out")

    return SimpleAgent(
        name=name,
        inport="in",
        outports=["out"],
        init_fn=init_fn,
        handle_msg=handle_msg,
    )


# Example (starter)
if __name__ == "__main__":
    from dsl.core import Network
    from dsl.block_lib.stream_generators import generate
    from dsl.block_lib.stream_recorders import RecordToList

    results = []
    net = Network(
        blocks={
            "gen": generate(["hello Jack", "hello there Jack", "goodbye there"], key="text"),
            "sim": make_similarity_agent_simple("hello there"),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sim", "in"),
            ("sim", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()
    print("Results (Tier 1):", results)
```

### ▶️ Run It
```bash
python3 -m dsl.examples.ch01_networks.simple_network

[]
```

## 🧠 Key Takeaways

- **SimpleAgent**  is specified by **init_fn** which initializes the agent and **handle_msg** which is the function applied to each message received by the agent.
- It is the parent class for many classes including generators, transformers and recorders.

## Sidebar: More about Document Similarity

```
import re
import math
from collections import Counter
from dsl.core import SimpleAgent

_word_re = re.compile(r"[A-Za-z']+")


def tokenize(text, stem=False):
    toks = [t.lower() for t in _word_re.findall(str(text))]
    if not stem:
        return toks
    # trivial stemmer: strip ing/ed/s
    out = []
    for t in toks:
        for suf in ("ing", "ed", "s"):
            if len(t) > len(suf) + 2 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out

# --- similarity metrics ---


def overlap_count(a, b):
    return len(set(a) & set(b))


def jaccard(a, b):
    A, B = set(a), set(b)
    return len(A & B) / len(A | B) if (A or B) else 1.0


def dice(a, b):
    A, B = set(a), set(b)
    return 2*len(A & B)/(len(A)+len(B)) if (A or B) else 1.0


def cosine_tf(a, b):
    ca, cb = Counter(a), Counter(b)
    num = sum(ca[t]*cb[t] for t in set(ca) | set(cb))
    den = math.sqrt(sum(v*v for v in ca.values())) * \
        math.sqrt(sum(v*v for v in cb.values()))
    return 0.0 if den == 0 else num/den


def edit_distance(a_str, b_str):
    a, b = a_str, b_str
    m, n = len(a), len(b)
    dp = list(range(n+1))
    for i in range(1, m+1):
        prev, dp[0] = dp[0], i
        for j in range(1, n+1):
            prev, dp[j] = dp[j], min(
                dp[j] + 1,                  # deletion
                dp[j-1] + 1,                # insertion
                prev + (a[i-1] != b[j-1])   # substitution
            )
    return dp[n]


METRICS = {
    "overlap": lambda ref, x: overlap_count(ref, x),
    "jaccard": lambda ref, x: jaccard(ref, x),
    "dice": lambda ref, x: dice(ref, x),
    "cosine": lambda ref, x: cosine_tf(ref, x),
    "edit": lambda ref, x: edit_distance(" ".join(ref), " ".join(x)),
}


def make_similarity_agent(reference_sentence: str, *, metric="jaccard", stem=False, name="SentenceSimilarityAgent"):
    ref_tokens = tokenize(reference_sentence, stem=stem)
    metric_fn = METRICS.get(metric)
    if metric_fn is None:
        raise ValueError(
            f"Unknown metric '{metric}'. Choose from {list(METRICS)}")

    def init_fn(agent):
        agent.state = {"ref": ref_tokens, "metric": metric, "stem": stem}
        print(
            f"[{name}] Initialized with ref='{reference_sentence}', metric={metric}, stem={stem}")

    def handle_msg(agent, msg, inport=None):
        toks = tokenize(msg, stem=agent.state["stem"])
        score = metric_fn(agent.state["ref"], toks)
        result = {"input": str(
            msg), "metric": agent.state["metric"], "score": round(score, 3)}
        print(f"[{name}] Input='{msg}' → {agent.state['metric']}={result['score']}")
        agent.send(result, outport="out")

    return SimpleAgent(
        name=name,
        inport="in",
        outports=["out"],
        init_fn=init_fn,
        handle_msg=handle_msg,
    )


# Example usage
if __name__ == "__main__":
    from dsl.core import Network
    from dsl.block_lib.stream_generators import generate
    from dsl.block_lib.stream_recorders import RecordToList

    results = []
    net = Network(
        blocks={
            "gen": generate(["hello Jack", "hello there Jack", "goodbye there"], key="text"),
            "sim": make_similarity_agent("hello there", metric="cosine", stem=True),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sim", "in"),
            ("sim", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()
    print("Results (Tier 2):", results)
```

---

### 🚀 Coming Up

How would you create a block that receives movie reviews, gives each movie a score by analyzing its review, and outputs both the review and its score?

👉 [**Next up: Chapter 2. Messages as Dictionaries.**](../ch02_keys/README.md)
