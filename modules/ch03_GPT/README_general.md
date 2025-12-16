# 3.5 • Simple AI demos from text

The following lines are helpful in inspecting output of AI agents that operate on texts. Run the program with your AI agent specified by a prompt, and your list of text documents.

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

AI agent that [extracts information from weather alerts](./README_WeatherAlerts.md)