# 3.3 • Simple AI demos from text

This page gives a short program that is used to give examples of AI agents operating on texts from a list. An agent is specified by a system prompt.

---

## What you’ll do
Create a network with three agents shown in the diagram below. 

```python
     +------------------+
     | source: iterator |
     |  yields msg      |
     | {"text": "..."}  |
     +------------------+
            |
            | stream of messages which are dicts
            | example: {"text": "The concert was terrible. I hated the performance."}
            |
            v
     +----------------------+
     | ai_agent enriches    |
     | msg it receives by   |
     |adding fields to msg  |
     +----------------------+
            |
            |example msg; {"text": "The concert...",
            |              "sentiment_score":  -9,
            |              "reason": "The words 'terrible'..."}
            v
     +------------------+
     |    print:        |
     |  kv_live_sink    |
     +------------------+
```

---

##  AI Simple Demo
In the program, **source** is an iterator that yields a text from a specified list of texts. **ai_agent** is an agent that calls OpenAI services with a specified system prompt. The function **ai_agent.enrich_dict** has a single message (a dict) as input where the dict has a field called ```text```. The function outputs a single message which is a dict which is the input message with additional fields supplied by ai_agent.

```python
# modules.ch03_openai.ai_simple_demo

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text


def ai_simple_demo(list_of_text, system_prompt):
    source = source_list_of_text(list_of_text)
    ai_agent = AgentOpenAI(system_prompt=system_prompt)
    g = network([(source.run, ai_agent.enrich_dict),
                 (ai_agent.enrich_dict, kv_live_sink)])
    g.run_network()

```

---

## Run an example with a specified list of texts and a system prompt
From the DisSysLab directory execute:
```bash
list_of_text = ...
system_prompt = ...
ai_simple_demo(list_of_text, system_prompt)
```


## 👉 Next
[Extract entities in a text](./README_entity.md)