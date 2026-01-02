<!-- modules/ch03_GPT/README_sentiment.md    -->

# 3.2 • AI agent: Sentiment Analysis

This module describes an example that uses an AI agent to score the sentiment of text. 

---

## What you’ll do
Create a network with three agents shown in the diagram below. The first agent is a source that generates a stream of reviews. Usually, the source would extract reviews from an RSS newsfeed or from social media posts. In this page the list of reviews is given in the source agent. 

The second agent in the network receives streams of reviews. It sends each review to an OpenAI service which adds a **sentiment score** in the range **−10..+10** and gives a short reason for the score. The third agent receives a stream of messages containing reviews, their scores and rationale, and the agent merely prints each message.

```python
     +------------------+
     | source: iterator |
     |  yields reviews  |
     +------------------+
            |
            | stream of reviews
            | example: "The concert was terrible. I hated the performance.",
            |
            v
     +----------------------+
     | AI agent determines  |
     | sentiment of each    |
     |        review        |
     +----------------------+
            |
            |example: sentiment_score: -9
            |  reason: The words 'terrible' and 'hated' clearly indicate ...
            v
     +------------------+
     |    print:        |
     |  kv_live_sink    |
     +------------------+
```

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

## AI Agent: Get Sentiment of Text

```python
# modules.ch03_GPT.sentiment

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text

# example data
list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

# system prompt for sentiment analysis
system_prompt = (
    "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. "
    "Give a brief reason. Return a JSON object with exactly the following format: "
    '{"sentiment_score": sentiment score, "reason": reason for the score}'
)

# Create source and AI agent
source = source_list_of_text(list_of_text)
ai_agent = AgentOpenAI(system_prompt=system_prompt)

#  Create and run network
g = network([(source.run, ai_agent.enrich_dict),
            (ai_agent.enrich_dict, kv_live_sink)])
g.run_network()
```

---

## Run the demo
From the DisSysLab directory execute:
```bash
python -m modules.ch03_openai.sentiment_from_list
```

You’ll see output like:
```
text:   The concert was terrible. I hated the performance.
sentiment_score:   -9
reason:   The words 'terrible' and 'hated' clearly indicate a very strong negative sentiment towards the concert and performance.
--------------------------------

text:   The book was okay, not too bad but not great either.
sentiment_score:   0
reason:   The sentiment is neutral as the statement expresses neither strong positive nor negative feelings, describing the book as average.
--------------------------------

text:   This is the best course on AI I've ever taken!
sentiment_score:   9
reason:   The phrase expresses strong positive enthusiasm and satisfaction with the course.
--------------------------------
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

## Try 

- Swap the source to **RSS** or **Jetstream** text and keep the same `agent_op` transformer.  
- Create a **keyword filter** transformer before the LLM call to reduce cost.  
- Record results to **JSONL** and plot sentiment over time (Module 5 + later examples).  
- Try **summarization** or **entity extraction** with a similar `AgentOpenAI` wrapper.

## 👉 Next
[Identify entities in a text](./README_entity.md)