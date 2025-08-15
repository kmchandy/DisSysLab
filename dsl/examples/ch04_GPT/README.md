# 🧩 Chapter 4 — AI Transformers

### 🎯 Goal
Learn how to create **AI blocks** easily.

---

## 📍 What We’ll Build

We’ll extend our three-block network with a GPT transformer:

- **Generator** – produces messages with a `"text"` field (short reviews).  
- **GPT Transformer** – uses a system prompt to analyze the text.  
- **Recorder** – saves the GPT-augmented messages.  

**Visual:**  
`[ Generator ] → [ GPT Transformer ] → [ Recorder ]`

---

## 💻 Code Example


```python
# dsl/examples/ch04_GPT/gpt_network.py

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerPrompt
from dsl.block_lib.stream_recorders import RecordToList

# Store results here
results = []

# Define the network
net = Network(
    blocks={
        "generator": GenerateFromList(
            items=[
                "The movie was fantastic!",
                "I didn’t like the food.",
                "Service was slow but friendly."
            ],
            key="text"
        ),
        "sentiment_analyzer": TransformerPrompt(
            system_prompt="You are a sentiment rater. Output a positivity score from 0 to 10.",
            input_key="text",
            output_key="sentiment",
        ),
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "sentiment_analyzer", "in"),
        ("sentiment_analyzer", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print(results)
```

## ▶️ Run It
```bash
python3 -m dsl.examples.ch04_GPT.gpt_network
```

## ✅ Example Output
```
[
    {"text": "The movie was fantastic!", "sentiment": "9"},
    {"text": "I didn’t like the food.", "sentiment": "2"},
    {"text": "Service was slow but friendly.", "sentiment": "6"}
]
```

## 🧠 Key Takeaways
- GPT can be used as just another transformer in the network.

- system_prompt defines what GPT should do.

- input_key specifies what part of the message is sent to GPT.

- output_key tells where the GPT result should be stored in the dictionary.

## ⏭️ Coming Up

✨ Next, we’ll go deeper into generators — learning how to build streams from numbers, files, and live data.