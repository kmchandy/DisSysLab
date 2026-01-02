<!--  modules.ch03_GPT.README_general.md    -->

# 3.5 • Simple networks of AI agents operating on text

The following code segment is a general framework for AI agents that operate on texts. You can use this framework for a variety of applications by specifying the prompt.

```python
# modules.ch03_GPT.ai_simple_demo

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