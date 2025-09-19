# Sinks

Sinks record streams of messages by storing in memory, writing to files, or printing to the console.

Sinks have one inport ("in") and no outports.

## File Layout

```
dsl/block_lib/sinks/
│
├── sink.py       # Base class Sink
├── sink_lib/  # Pure-Python helpers for common functions to record streams. Used by `Sink`
      ├── common_sinks.py  # common sink helpers
└── README.md     # This file
```


Examples
### 1. Record messages in a Python list
```
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list

results = []
sink = Sink(name="Collector", record_fn=record_to_list(results))
```
   

### 2. Write messages to a text file
```
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_file

sink = Sink(name="FileWriter", record_fn=record_to_file("out.txt"))
```

The file out.txt will contain:
```
apple
banana
```

### 3. Pretty-print messages to the console

```
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_console

sink = Sink(name="Printer", record_fn=record_to_console(prefix=">> "))
```

Console output:
```
>> apple
>> banana
```

## Add your own functions to sink_lib.

You can create your own sink function by modifying the examples here or developing your own. For example, to send every message to a web API:

```
import requests
from dsl.block_lib.sinks.sink import Sink

def record_to_api(url: str):
    def _fn(agent, msg):
        requests.post(url, json={"payload": msg})
    return _fn

sink = Sink(name="APISink", record_fn=record_to_api("https://example.com/ingest"))
```

## Sink Cheat Sheet (Quick lookup)

Use
```
Sink(name=..., record_fn=...)
```

where ```record_fn(agent, msg)``` is a function that consumes messages with a side effect of recording the message. 

### A. Record to list or set
```
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list, record_to_set

results = []
sink = Sink(name="Collector", record_fn=record_to_list(results))

unique = set()
sink = Sink(name="UniqueCollector", record_fn=record_to_set(unique))
```

### B. Record to files
```
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_file, record_to_jsonl

sink = Sink(name="Lines", record_fn=record_to_file("out.txt", key=None))
sink = Sink(name="JSON", record_fn=record_to_jsonl("out.jsonl", key="data"))
```

### C. Show on console or record to log file
```
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_console, record_to_logfile

sink = Sink(name="Printer", record_fn=record_to_console(prefix=">> "))
sink = Sink(name="Logger", record_fn=record_to_logfile("events.log"))
```