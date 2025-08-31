# Assistant Spec v1: AL — A Conversational Design Partner for Distributed Systems

## 🎯 Purpose

AL ("Agent for Learning") is an OpenAI-powered assistant that helps non-programmers design distributed systems by interacting in natural language. It guides users through creating and connecting reusable blocks that represent components in a distributed application.

This specification defines the v1 behavior of AL.

---

## 🧑‍🎓 Target Users

- Beginners with no programming experience
- Educators and students
- Users familiar with AI prompts but not system design

---

## 🧱 Core Concepts

### Network Representation

AL internally maintains a single `network` dictionary:

```python
network = {
    "blocks": {
        "gen": {
            "type": "generate",
            "function": "GenerateFromList",
            "parameters": {"values": ["hello", "world"]}
        },
        "xf": {
            "type": "transform",
            "function": "GPT_Prompt",
            "parameters": {
                "template": "sentiment_analysis",
                "input_key": "text",
                "output_key": "sentiment"
            }
        },
        "rec": {
            "type": "record",
            "function": "RecordToFile",
            "parameters": {"filename": "results.json"}
        }
    },
    "connections": [
        {"from": "gen", "from_port": "out", "to": "xf", "to_port": "in"},
        {"from": "xf", "from_port": "out", "to": "rec", "to_port": "in"}
    ]
}
```

This can be exported as either:

- Python code compatible with DisSysLab
- YAML for future editing

---

## 🧩 Supported Block Types

| Block Type | Purpose                          | Functions Allowed                      |
| ---------- | -------------------------------- | -------------------------------------- |
| generator  | Emit initial messages            | `GenerateFromList`, `GenerateFromFile` |
| transform  | Modify/analyze messages with GPT | `GPT_Prompt` (via `PromptToBlock`)     |
| record     | Store or display results         | `RecordToFile`, `RecordToList`         |
| fan-in     | Merge multiple streams           | `MergeAsynch`, `MergeSynch`            |
| fan-out    | Split streams                    | `Broadcast`                            |

Users select from this library; no arbitrary functions or Python code allowed.

---

## 🔁 Interaction Model

- AL is a **guided assistant**, not a rigid wizard
- Conversations are **non-linear** and **stateful**
- Users can revisit and edit blocks
- AL keeps track of current network and blocks in progress

### Examples of Supported Commands:

| User Says                       | AL Behavior                                           |
| ------------------------------- | ----------------------------------------------------- |
| "Create a generator called gen" | Adds `gen` with type `generate`; prompts for function |
| "I’d like to specify gen"       | Enters edit mode for block `gen`                      |
| "Add a transformer xf"          | Adds `xf` block with type `transform`                 |
| "Connect gen to xf"             | Adds connection from `gen.out` to `xf.in`             |
| "Show me the network"           | Summarizes blocks and connections                     |

---

## 🧠 Assistant Capabilities (v1)

AL supports these core actions:

- `create_block(name, type)`
- `set_block_function(name, function, parameters)`
- `connect_blocks(from_block, to_block)`
- `specify_block(name)` (enter edit mode)
- `describe_block(name)`
- `summarize_network()`
- `list_blocks()`
- `delete_block(name)`
- `export_to_python()`
- `export_to_yaml()`

---

## 🚦 Design Constraints

- Only one network active per session
- User cannot create arbitrary Python code
- No NumPy or Scikit-learn support in v1
- User input is natural language; AL interprets and constrains it to valid options

---

## 📤 Export Formats

1. **Python**: executable with `Network(blocks=..., connections=...)`
2. **YAML**: editable spec that can be reloaded later

---

## 📌 Notes for Future Versions

- Support multiple networks
- Add visual network editor (drag-and-drop UI)
- Support user-defined prompts or functions
- Add undo/redo functionality

---

## 📅 Development Notes

- Confirmed as v1 spec on August 7, 2025
- User will work on this intermittently, unavailable August 22–28

## Running Virtual Environment venv
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```