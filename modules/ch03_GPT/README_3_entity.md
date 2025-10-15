# 3.2 • Transformer — Entity Extraction

This page shows how to use transformers using OpenAI to **extract entities** -- people, places, organizations -- from text.

---

## What you’ll do
Run a tiny script that sends each text to an OpenAI agent and **adds an `entities` field** to each dict with the extracted entities.

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

## The Entity Extraction Demo

```python
# modules.ch03_openai.entities_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi.",
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]

def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------

system_prompt = "Extract entities."
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent, add result under 'entities'
# -----------------------------------------------------------

def agent_op(v):
    v["entities"] = agent.fn(v["text"])
    return v

# -----------------------------------------------------------
# 4) Sink — pretty print dict keys/values
# -----------------------------------------------------------

def print_sink(v):
    print("==============================")
    for key, value in v.items():
        print(key)
        print(value)
        print("______________________________")
    print("")

# -----------------------------------------------------------
# 5) Wire and run
# -----------------------------------------------------------

g = network([(from_list_of_text, agent_op), (agent_op, print_sink)])
g.run_network()
```

---

## Run the demo
```bash
python3 -m modules.ch03_openai.entities_from_list
```

You’ll see output like (shape depends on your `AgentOpenAI` implementation and prompt):
```
==============================
text
Obama was the first African American president of the USA.
______________________________
entities
{'entities': [{'type': 'PERSON', 'name': 'Barack Obama'},
              {'type': 'NORP', 'name': 'African American'},
              {'type': 'GPE', 'name': 'USA'}]}
______________________________
```

---

## Parameters you can modify

| Parameter | Type | Description |
|-----------|------|-------------|
| **list_of_text** | list[str] | The input items to process. Replace with RSS text, Bluesky posts, etc. |
| **system_prompt** | str | Guides the LLM about what to extract and the output format. |
| **agent_op** | callable | The transformer that invokes the LLM and writes to `entities`. |
| **AgentOpenAI(...)** | ctor args | If supported, pass model/temperature/max tokens to control cost/latency. |
| **agent.fn(x)** | callable | The callable that runs the LLM for a single input string. |

> _Tip:_ For consistent downstream processing, make the prompt request a **strict JSON** schema, e.g.:  
> “Return JSON: `{"entities":[{"type":"PERSON","name":"..."}, ...]}`. No text outside JSON.”

---

## Troubleshooting

- **Auth errors**: Ensure `OPENAI_API_KEY` is set in the environment seen by the Python process.  
- **Unexpected output format**: Tighten the system prompt to require strict JSON with fixed keys.  
- **Long/slow responses**: Reduce input length, switch to a cheaper/faster model, or add batching/rate limiting.  
- **Privacy**: Avoid sending sensitive or personally identifiable text to external APIs without consent.

---

## Next steps
- Swap the source to **RSS** or **Jetstream** to extract entities from live feeds.  
- Chain a transformer to **count entities** by type or name and compute frequencies.  
- Record results to **JSONL** for later analysis (Module 5), or visualize top entities.  
- Try a **hybrid prompt** that extracts both entities **and** sentiment per entity.
