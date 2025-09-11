# DisSysLab Naming Conventions (Student Edition)

**Convention:** **From Source → Transform message → To Sink**  

- **FromX** — where data comes **from**
- **VerbY** — what the app **does** to each message
- **ToZ** — where data goes **to**
- 
---

### Sources of message streams (start with **From**)
Use these to start a stream.
- `FromList`
- `FromCSV`
- `FromJSONL`
- `FromFileLines`
- `FromDirectory` *(glob of files)*
- `FromTimer`
- `FromRandomInts`
- `FromRSS`

### Transforms of message streams (plain-English **verbs**)
Use a verb that describes exactly what happens.

**Annotate (add fields):**
- `AddSentiment`, `AddTime`, `AddID`, `AddSourceTag`

**Extract (pull parts out):**
- `ExtractEntities`, `ExtractNumbers`, `ExtractEmails`

**Filter (drop messages):**
- `FilterEmpty`, `FilterByValue`, `FilterRegex`

**Schema ops:**
- `SelectKeys`, `RenameKey`, `DropKeys`

**Convert / Compute / Normalize / Classify (change representation):**
- `ConvertToJSON`, `ComputeHash`, `NormalizeCase`, `ClassifySentiment`

> Rule of thumb: **Add*** keeps the original message and **adds** a field.  
> **Classify/Convert/Compute** produce a new value or shape.

### Sinks of message streams (start with **To**)
Use these to end a stream.
- `ToConsole` *(alias: `Print` is okay for discoverability)*
- `ToList`
- `ToFile`
- `ToJSONL`
- `ToLogfile`


##  “To do X, use Y”

- I want to genarate messages from a Python list → **FromList**  
- I want to create messages from a CSV file → **FromCSV**  
- I want each line in JSON Lines to be a message → **FromJSONL**  
- I want to add timestamps to messages → **AddTime**  
- I want a `sentiment` field added to messages → **AddSentiment**  
- I want to replace each message by a summary → **Summarize**  
- I want to keep only some fields in a message dict → **SelectKeys**  
- I need to rename a field in message dict → **RenameKey**  
- I want to remove None messages from a stream→ **FilterNone**  
- I want to print results → **Print**  
- I want each message to be stored in one JSON line → **ToJSONL**

---


## Starter Set (v1)

**Sources:** `FromList`, `FromCSV`, `FromJSONL`, `FromFileLines`, `FromTimer`, `FromRandomInts`  
**Transforms (annotate/extract):** `AddSentiment`, `AddTime`, `ExtractEntities`, `SelectKeys`  
**Sinks:** `ToConsole`, `ToList`, `ToFile`, `ToJSONL`

---

## Notes

-  If a name doesn’t “sound right” in *From → Verb → To* form, as in **FromCSV → AddSentiment → ToConsole**  then pick a clearer verb.
