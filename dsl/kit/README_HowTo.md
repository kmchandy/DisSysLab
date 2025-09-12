
# Tips: How to Pick Blocks

We start with a simple pipeline. 
Later we will consider networks with arbitrary graph structures with multiple sources, actions, and sinks. 

## Pipeline model 

**From block → do something block .. → do something block → To block**  


- Start generating messages **From** some source,  **do** something to the message stream in one or more steps, and send the results **To** some sink. 
---

## Quick Example

```
from dsl.kit import FromList, Uppercase, Print, pipeline

net = pipeline([
    FromList(["hello", "world"]),
    Uppercase(),  # receive message and send its uppercase version.
    ToConsole()           
])
net.compile_and_run()
# HELLO
# WORLD
```

---

## Quick picks — “If you want to do X, use class Y”

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

**Sinks (where output messages go):**
- Print to the screen → `ToConsole()` (alias: `Print()`)
- Save as JSON Lines → `ToJSONL("results.jsonl")`
- Save plain text (one line per message) → `ToFile("results.txt")`
- Collect in a Python list → `ToList(target_list)`

---

## Common tiny pipeline patterns

**Annotate: add field sentiment to a message dict**
```
FromRSS(url=...) → AddSentiment() → ToJSONL("news.jsonl")
```

**Transform value**
```
FromList(["hi","there"]) → Uppercase() → Print()
```

**Trim schema: remove keys and values from a message dict**
```
FromCSV("data.csv") → SelectKeys(["name","email"]) → ToJSONL("people.jsonl")
```

**Extract info**
```
FromList(["Mount Everest is ..."]) → ExtractEntities() → Print()
```

---

## Try these variations in a couple of minutes

1. Swap `Uppercase()` for `AddSentiment()` and observe how the message shape changes.
2. Change the sink from `ToConsole()` to `ToJSONL("out.jsonl")`, open the file, and inspect a few lines.
3. Replace `FromList([...])` with `FromCSV("sample.csv")` and add `SelectKeys([...])`.

---

## Use the Wizard

Prefer menus over typing? The Wizard builds and runs the same pipelines:

```
python -m dsl.user_interaction.wizard --lesson step1
```


