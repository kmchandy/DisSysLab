<!--  modules.ch03_GPT.README_summarizer.md    -->

# 3.4 • AI Agent — Summarize Text

This page is an example of an AI agent that summarizes a text.

---

## What you’ll do
Run a network of three agents -- a source, an ai agent, and a sink that prints results.  The ai agent sends text to an OpenAI agent which summarizes the text and adds a **summary** fields to each message.

```python
     +------------------+
     | generate stream  |
     | of documents     |
     +------------------+
            |
            | stream of documents
            | example: "A play is a form of theatre..."
            |
            v
     +----------------------+
     | AI agent determines  |
     |  a summary of each   |
     |    document          |
     +----------------------+
            |
            |example: "A play is a scripted theatrical..."
            |  
            |
            v
     +------------------+
     |  kv_live_sink    |
     +------------------+
```

---

## Setup (once)


As in the [earlier page on sentiment scoring](README_sentiment.md)

---


## The Summarizer Demo
```python
# modules.ch03_GPT.summary_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text

list_of_text = [
    (
        "A play is a form of theatre that primarily consists of"
        " script between speakers and is intended for acting rather"
        " than mere reading. The writer and author of a play is"
        " known as a playwright. Plays are staged at various levels,"
        " ranging from London's West End and New York City's"
        " Broadway – the highest echelons of commercial theatre in"
        " the English-speaking world – to regional theatre, community"
        " theatre, and academic productions at universities and schools."
    ),
    ("Artificial general intelligence (AGI)—sometimes called human‑level"
     "intelligence AI—is a type of artificial intelligence that would"
     "match or surpass human capabilities across virtually all cognitive tasks."

     "Some researchers argue that state‑of‑the‑art large language models (LLMs)"
     "already exhibit signs of AGI‑level capability, while others maintain that"
     "genuine AGI has not yet been achieved. Beyond AGI, artificial"
     "superintelligence (ASI) would outperform the best human abilities across"
     "every domain by a wide margin."
     )
]

system_prompt = (
    "Return a JSON document {'summary': x}"
    "where x is a summary of the input text."
)

source = source_list_of_text(list_of_text)
ai_agent = AgentOpenAI(system_prompt=system_prompt)

g = network([(source.run, ai_agent.run),
             (ai_agent.run, kv_live_sink)])
g.run_network()


```

---

## Run the demo
In the DisSysLab directory execute:
```bash
python -m modules.ch03_GPT.summary_from_list
```

You’ll see output containing the original `text` and a one-line `summary`, for example:
```
text
A play is a form of theatre that primarily consists of script …

summary
A play is a theatrical work written by a playwright and intended for performance, staged from major commercial venues to community and academic productions.
```

---

## 👉 Next

Look at a [short program that you can use to test AI agents](./README_general.md) or 
an AI agent that [extracts information from weather alerts](./README_WeatherAlerts.md)