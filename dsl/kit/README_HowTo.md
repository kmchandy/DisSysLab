
# How to Pick Blocks (Student How-To)

**Mental model:** **From → (do something) → To**  
You always: start **From** something, optionally **do** something to each message, and send it **To** somewhere.

---

## 60-second win

```python
from dsl.kit import FromList, Uppercase, Print, pipeline

net = pipeline([
    FromList(["hello", "world"]),
    Uppercase(),
    Print()           # alias of ToConsole()
])
net.compile_and_run()
# HELLO
# WORLD
```

---

## Quick picks — “If you want X, use Y”

**Sources (start a stream):**
- From a Python list → `FromList([...])`
- From a CSV file → `FromCSV("data.csv")`
- From a JSON Lines file → `FromJSONL("data.jsonl")`
- From lines in a text file → `FromFile("notes.txt")`
- From an RSS feed → `FromRSS(url="https://...")`
- From a timer / random ints → `FromTimer(...), FromRandomInts(...)`

**Transforms (do something to each message):**
- Add a `sentiment` field → `AddSentiment()`
- Make text uppercase → `Uppercase()`
- Keep only some fields → `SelectKeys(["text","time"])`
- Extract entities from text → `ExtractEntities()`

> Rule of thumb:  
> - **Add*** = annotate (keep the original message and add a field)  
> - **Classify/Convert/Compute** = replace or transform the output value  
> - **Select/Rename/Drop** = change the **schema** (which keys exist)

**Sinks (where messages go):**
- Print to the screen → `ToConsole()` (alias: `Print()`)
- Save as JSON Lines → `ToJSONL("results.jsonl")`
- Save plain text (one line per message) → `ToFile("results.txt")`
- Collect in a Python list → `ToList(target_list)`

---

## Common tiny patterns

**Annotate (add fields)**
```python
FromRSS(url=...) → AddSentiment() → ToJSONL("news.jsonl")
```

**Transform value**
```python
FromList(["hi","there"]) → Uppercase() → Print()
```

**Trim schema**
```python
FromCSV("data.csv") → SelectKeys(["name","email"]) → ToJSONL("people.jsonl")
```

**Extract info**
```python
FromList(["Mount Everest is ..."]) → ExtractEntities() → Print()
```

---

## Try these variations (2–3 minutes)

1. Swap `Uppercase()` for `AddSentiment()` and observe how the message shape changes.
2. Change the sink from `Print()` to `ToJSONL("out.jsonl")`, open the file, and inspect a few lines.
3. Replace `FromList([...])` with `FromCSV("sample.csv")` and add `SelectKeys([...])`.

---

## Use the Wizard (zero friction)

Prefer menus over typing? The Wizard builds and runs the same pipelines:

```bash
python -m dsl.user_interaction.wizard --lesson step1
```

