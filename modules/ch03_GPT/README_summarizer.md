# 3.4 • Transformer — Summarize Text

This page shows how to use a transformer using OpenAI to **summarize text**.

---

## What you’ll do
Run a tiny script that sends each text to an OpenAI agent and **adds a one-line summary** to the message dict.

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
     |    print         |
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

> _Note:_ This example uses `dsl.extensions.agent_openai.AgentOpenAI`, which looks for `OPENAI_API_KEY`.

---

## The Summarization Demo

```python
# modules.ch03_GPT.summary_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

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


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------


system_prompt = "Summarize the text in a single line."
make_summary = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent, add result under 'summary'
# -----------------------------------------------------------


def add_summary_to_msg(msg):
    msg["summary"] = make_summary(msg["text"])
    return msg

# -----------------------------------------------------------
# 4) Sink — print
# -----------------------------------------------------------


def print_sink(msg):
    print("==============================")
    for key, value in msg.items():
        print(key)
        print(value)
        print("______________________________")
    print("")

# -----------------------------------------------------------
# 5) Connect functions and run
# -----------------------------------------------------------


g = network([(from_list_of_text, add_summary_to_msg),
            (add_summary_to_msg, print_sink)])
g.run_network()

```

---

## Run the demo
In the DisSysLab directory execute:
```bash
python -m modules.ch03_openai.summary_from_list
```

You’ll see output containing the original `text` and a one-line `summary`, for example:
```
text
A play is a form of theatre that primarily consists of script …

summary
A play is a theatrical work written by a playwright and intended for performance, staged from major commercial venues to community and academic productions.
```

---

## Parameters you can modify

| Parameter | Type | Description |
|-----------|------|-------------|
| **list_of_text** | list[str] | Replace with your own texts (e.g., RSS article bodies). |
| **system_prompt** | str | Controls style/length (e.g., “bullet list,” “max 20 words,” “include keywords”). |
| **add_key** | str | Dict key where the summary is stored (default `"summary"`). |
| **AgentOpenAI(...)** | ctor args | If supported, override model/temperature/max tokens. |
| **agent.fn(x)** | callable | The callable that runs the LLM for a single string input. |

> _Tip:_ To ensure consistent formatting, ask for **strict JSON**:  
> “Return JSON `{ "summary": "<one line>" }` with no extra text.”

---

## Troubleshooting

- **Auth errors:** Ensure `OPENAI_API_KEY` is available in your shell/environment.  
- **Very long outputs:** Tighten the prompt (e.g., “≤ 20 words”), reduce input length, or change model params.  
- **Latency / cost:** Batch fewer items, trim text, or switch to a faster/cheaper model if supported.

---

## Try
- Chain with **entity extraction** or **sentiment** to build richer annotations.  
- Record results to **JSONL/CSV** (Module 5) and evaluate summary quality over time.  
- Add a pre-transform to **truncate** or **clean** inputs (strip boilerplate, HTML).

## 👉 Next
[Develop a simple graph that extracts data from weather alerts](./README_5_WeatherAlerts.md) w