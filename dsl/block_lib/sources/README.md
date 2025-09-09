# Sources

Sources generate messages and send them to blocks in the network.
- Sources turn Python objects -- files, APIs, or user input -- into a stream of messages.

---

## File Layout
```
dsl/block_lib/sources/
│
├── source.py # Base class Source (inherits from SimpleAgent)
├── source_lib.py # Pure-Python helpers for common generators
└── README.md # This file
```

- **`source.py`** defines the  `Source` base class which uses simple functions in ***source_lib.py*** to create blocks.
- **`source_lib.py`** contains simple helper functions (`gen_list`, `gen_list_as_key`, …) for ***source.py***.

---

## Examples

### 1. Generate messages from a list
```
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib import gen_list

# Create a generator that yields 'apple', 'banana'
gen = gen_list(['apple', 'banana'])

src = Source(name="FruitSource", generator_fn=gen)
```

The source produces:
```
apple
banana
```

### 2. Generate messages as key–value dicts from a list
```
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib import gen_list_as_key

gen = gen_list_as_key(['apple', 'banana'], key='fruit')
src = Source(name="FruitSource", generator_fn=gen)
```

This source sends:

```
{"fruit": "apple"}
{"fruit": "banana"}
```

### 3. Generate messages with timestamps from a list
```
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib import gen_list_as_key_with_time

gen = gen_list_as_key_with_time(['a', 'b'], key='text')
src = Source(name="TextSource", generator_fn=gen)
```

This source sends:

```
{"text": "a", "time": "2025-09-08 12:34:56"}
{"text": "b", "time": "2025-09-08 12:34:56"}
```

## Notes

- *** Why does a source have no inports?***
Sources are “entry points.” They don’t get messages from other blocks. They produce messages from sources such as RSS streams.

- *** Why does a source have only one outport?*** 
  Sources produce one stream of messages. If you need to fan-out to multiple streams, use a ***fanout*** block after the source.

- *** When to have messages that are dicts?**
Messages as dicts let you attach fields like "data", "source", "time" to a message. This allows you to easily include results of later transformations in a message. For example if "data" is text from an RSS feed and a transformation determines the sentiment (positive or negative) of the feed then you can add a "sentiment" field to the message.

## Add your own functions to source_lib.

You can modify the functions in ***source_lib*** to create your own functions, or you can write your own generator. For example, you may want a source that generates "N" random numbers between "LOW" and "HIGH":

```
import random
from dsl.block_lib.sources.source import Source

def my_generator(N, LOW, HIGH):
    i = 0
    while i < N:
        yield random.randint(LOW, HIGH)
        n += 1

src = Source(name="Rand_N", generator_fn=my_generator, N=5, LOW=1, HIGH=10)
```

# Source Cheat Sheet (Quick lookup)
Use ``Source(name=..., generator_fn=...)`` where generator_fn(*args, **kwargs) returns an iterator / generator that yields one message at a time.

## A. Lists & simple values

```
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib import (
    gen_list, gen_list_as_key,
    gen_repeat, gen_range, gen_counter
)
```

#### Plain list
```
src = Source(name="Fruits", generator_fn=gen_list, items=["apple", "banana"])
```

#### List → dicts with a key
```
src = Source(name="FruitsKV", generator_fn=gen_list_as_key,
             items=["apple", "banana"], key="fruit")
```

#### Repeat a value N times (or forever with times=None)
```
src = Source(name="Ping", generator_fn=gen_repeat, value="ping", times=3)
```

#### Numeric sequences
```
src = Source(name="Range10", generator_fn=gen_range, start=0, stop=10, step=2)
src = Source(name="Counter", generator_fn=gen_counter, start=100, step=5, times=4)
```


## B. Files & folders

```
from dsl.block_lib.sources.source_lib import gen_file_lines, gen_jsonl, gen_csv_rows, gen_dir_files

# Lines from a text file (strips by default)
src = Source(name="Lines", generator_fn=gen_file_lines, path="notes.txt", strip=True)

# JSON Lines (.jsonl), one JSON object per line
src = Source(name="JSONL", generator_fn=gen_jsonl, path="data.jsonl")

# CSV rows (as dicts via csv.DictReader)
src = Source(name="CSV", generator_fn=gen_csv_rows, path="people.csv")

# File paths matching a glob pattern (e.g., all PNGs)
src = Source(name="Images", generator_fn=gen_dir_files, pattern="images/**/*.png")
```

## C. Time & randomness
```
from dsl.block_lib.sources.source_lib import gen_timer_interval, gen_random_ints, gen_poll

# Tick every 0.5s, N times; yields {"time": <iso8601>} (add your own payload if needed)
src = Source(name="Ticker", generator_fn=gen_timer_interval, every_s=0.5, count=5)

# Random integers (finite or infinite if count=None)
src = Source(name="Rand", generator_fn=gen_random_ints, low=1, high=100, count=10)


# Poll a function periodically (e.g., read a sensor or API wrapper you wrote)
def read_temp():
    # return a Python object (number/dict/str) — it becomes the message
    return {"sensor": "t1", "celsius": 21.4}

src = Source(name="Therm", generator_fn=gen_poll, fn=read_temp, every_s=2.0, count=3)
```