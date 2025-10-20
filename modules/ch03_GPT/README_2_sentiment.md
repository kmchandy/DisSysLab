# 3.2 • Transformer — Sentiment Analysis

This page shows how to use **AI-based transformers**. This example uses OpenAI to score the sentiment of text. You can use AI providers in addition to OpenAI. Other types of transformers are covered in later modules.

A transformer function takes one input and returns one value. In this example the function calls an OpenAI agent.

---

## What you’ll do
Run a tiny script that sends each text to an OpenAI agent which adds a **sentiment score** in the range **−10..+10** and gives a short reason.

---

## Setup (once)
```bash
pip install openai rich
```

Set your OpenAI API key (choose one):

**macOS / Linux**
```bash
export OPENAI_API_KEY="sk-…your key…"
```

**Windows (PowerShell)**
```powershell
$env:OPENAI_API_KEY="sk-…your key…"
```

> _Note:_ The example uses `dsl.extensions.agent_openai.AgentOpenAI`, which expects your key in `OPENAI_API_KEY`.

---

## The Sentiment Demo

```python
# modules.ch03_GPT.sentiment

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------


system_prompt = (
    "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. "
    "Give a brief reason. Return a JSON object with exactly the following format: "
    '{"sentiment_score": sentiment score, "reason": reason for the score}'
)
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent and enrich the message
# -----------------------------------------------------------


def compute_sentiment(msg):
    # Make a dict from the json str response of the agent
    sentiment_score_and_reason_json = json.loads(agent.fn(msg["text"]))
    # enrich the message by adding sentiment_score and reason fields
    msg.update(sentiment_score_and_reason_json)
    return msg

# -----------------------------------------------------------
# 4) Sink — print values
# -----------------------------------------------------------


def print_sink(msg):
    for key, val in msg.items():
        print(f"{key}:   {val}")
    print("--------------------------------")
    print()

# -----------------------------------------------------------
# 5) Connect functions and run network
# -----------------------------------------------------------


g = network([(from_list_of_text, compute_sentiment),
             (compute_sentiment, print_sink)])
g.run_network()

```

---

## Run the demo
```bash
python -m modules.ch03_openai.sentiment_from_list
```

You’ll see output like:
```
{'text': 'The concert was terrible. I hated the performance.',
 'sentiment': {'score': -8, 'reason': 'Strong negative language'}}
{'text': 'The book was okay, not too bad but not great either.',
 'sentiment': {'score': 0, 'reason': 'Mixed, neutral overall'}}
{'text': "This is the best course on AI I've ever taken!",
 'sentiment': {'score': 9, 'reason': 'Highly positive wording'}}
```

*(Exact structure/content depends on your AgentOpenAI implementation.)*

---

## Parameters you can modify

| Parameter | Type | Description |
|-----------|------|-------------|
| **list_of_text** | list[str] | The input items to classify. Replace with RSS text, Bluesky posts, etc. |
| **system_prompt** | str | Guides the LLM (scoring range, style, and reasoning). |
| **add_key** | str | Dict key where the sentiment result is stored (e.g., `"sentiment"`). |
| **AgentOpenAI(...)** | ctor args | If supported in your implementation, you can pass model/temperature/max tokens. |
| **agent.fn(x)** | callable | The callable that runs the LLM on a single input string. |

> _Tip:_ Keep the system prompt **short and specific**. If you want just a number, ask for “**JSON with {score:int, reason:str}**” or just `score`.

---

## Troubleshooting

- **Auth errors**: Ensure `OPENAI_API_KEY` is set in the environment seen by the Python process.  
- **Rate limits / timeouts**: Add basic retry/backoff in `AgentOpenAI` or slow the input source.  
- **Unexpected output format**: Tighten the prompt (e.g., “Return JSON with keys `score` and `reason` only.”).  
- **Cost control**: Use small batches or shorter inputs; consider cheaper models if your Agent supports a model override.

---

## Next steps

- Swap the source to **RSS** or **Jetstream** text and keep the same `agent_op` transformer.  
- Create a **keyword filter** transformer before the LLM call to reduce cost.  
- Record results to **JSONL** and plot sentiment over time (Module 5 + later examples).  
- Try **summarization** or **entity extraction** with a similar `AgentOpenAI` wrapper.
