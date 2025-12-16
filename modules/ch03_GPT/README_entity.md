# 3.2 • AI Agent — Identify Entities

This page is an example of an AI agent that **identifies entities** -- people, places, organizations -- in a text.

---

## What you’ll do
Run a network of three agents -- a source, an ai agent, and a sink that prints results.  The ai agent sends text to an OpenAI agent and **adds an `entities` field** to each message.

```python
     +------------------+
     | generate stream  |
     | of news articles |
     +------------------+
            |
            | stream of articles
            | example: "BRICS is an organization of Brazil, Russia, .."
            |
            v
     +----------------------+
     | AI agent determines  |
     | entities in  each    |
     |        article        |
     +----------------------+
            |
            |example:
            |  {"Organization": ["BRICS"], "Country": ["Brazil, .."]}
            |
            v
     +------------------+
     |   kv_live_sink   |
     +------------------+
```

---

## Setup 


As in the [previous page on sentiment scoring](README_sentiment.md)


## The Entity Extraction Demo
```python
# modules.ch03_GPT.entities_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi.",
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]

system_prompt = (
    "Your task is to read the input text and extract entities"
    "such as names of people, organizations, countries and locations."
    "Return a JSON array of the entities found in the text where the key is"
    " the type of entity (e.g., Person, Organization, Location) and the value"
    "is the list of entities of that type. For example"
    '{"Person": ["Obama", "Modi"], "Location": ["USA", "New Delhi"]}'
)


source = source_list_of_text(list_of_text)
ai_agent = AgentOpenAI(system_prompt=system_prompt)

g = network([(source.run, ai_agent.enrich_dict),
             (ai_agent.enrich_dict, kv_live_sink)])
g.run_network()

```

---

## Run the demo
```bash
python3 -m modules.ch03_openai.entities_from_list
```

You’ll see output like
```
----------------------------------------                                             
                                                                                     
Location                                                                             
- India                                                                              
- New Delhi                                                                          
                                                                                     
Person                                                                               
- Narendra Modi                                                                      
                                                                                     
text                                                                                 
The capital of India is New Delhi and its Prime Minister is Narendra Modi.           
                                                                                     
----------------------------------------                                             
                                                                                     
Location                                                                             
- USA                                                                                
                                                                                     
Person                                                                               
- Obama                                                                              
                                                                                     
text                                                                                 
Obama was the first African American president of the USA. 

```


## 👉 Next
[Agent that summarizes a text](./README_summarizer.md)