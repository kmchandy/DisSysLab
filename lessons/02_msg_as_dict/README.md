# 🧩 Lesson 2 — Messages as Dictionaries

### 🎯 Goal
Use **messages as dictionaries** to attach information -- such as `data source`, `time created`, or `rating_score` -- to a message.

---

## 📍 Example

We’ll create a three-block network, as in chapter 1, except that now messages are dicts.

**Blocks in this example:**
- block name: **"source"**, 
  - execution: **FromListWithKey((reviews))** – Generate a stream consisting of messages where each message is a dict with a single key-value pair where the key is "review" and the value is text - a review of an article. Example of a message {"review": "The movie was great."}
- block name: **"add_sentiment"**, 
  - execution: **AddSentiment** – Receives a stream of messages on inport "in"; computes the sentiment of each message and adds a key-value pair to the message where the key is "sentiment" and the value is the sentiment of the message. Example output message: {"review": "The movie was great.", "sentiment": "positive"}
  - (We use a simple function to compute sentiment in this example. Later, we give examples that compute sentiment using AI functions from libraries provided by OpenAI and other organizations.)
- block name: **"sink"**, 
  - execution **ToConsole** – Receives a stream of messages on inport "in" and prints the messages on the console.

---


## 💻 Code Example

```
# lessons.02_msg_as_dict.example_dict.py
from dsl.kit import Network, FromListWithKey, AddSentiment, ToConsole


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def test_transform_simple_sentiment():

    network = Network(
        blocks={
            "source": FromListWithKey(items=reviews, key="review"),
            "add_sentiment": AddSentiment(input_key="review", add_key="sentiment"),
            "sink": ToConsole()
        },
        connections=[
            ("source", "out", "add_sentiment", "in"),
            ("add_sentiment", "out", "sink", "in")
        ]
    )
    network.compile_and_run()


if __name__ == "__main__":
    test_transform_simple_sentiment()
```

## ▶️ Run It
```
python -m lessons.02_msg_as_dict.example_dict
```

## ✅ Output
```
[  
    {'review': 'The movie was great. The music was superb!', 'sentiment': 'Positive'}
    {'review': 'The concert was terrible. I hated the performance.', 'sentiment': 'Negative'}
    {'review': 'The book was okay, not too bad but not great either.', 'sentiment': 'Neutral'}
    {'review': "This is the best course on AI I've ever taken!", 'sentiment': 'Positive'}
]
```

## Useful keys in messages such as time
A useful key in a dict message is the time at which the message was generated at the source or the time at which a block added a field to the message. You can attach a key-value pair -- `"time": time` - to a message by calling **FromListWithKeyWithTime**, see the program in 'lessons.02_msg_as_dict.example_time`. An example of a line of the output is:
```
{'review': 'The movie was great.',  
'time': '2025-09-12 21:26:33', 
'sentiment': 'Positive'}
```

## 🧠 Key Takeaways

- Messages can be dictionaries with multiple fields.

- Blocks can add fields such as "source", "time", and "sentiment_value" to a message.

### 🚀 Coming Up

The examples in this page were pipelines. But what if your application required a different type of network? Next you will use fan-in and fan-out blocks to build arbitrary networks. We begin with fan-out blocks. A fan-ou

👉 [**Next up: Chapter 3 — Fan-In & Fan-Out Networks.**](../ch03_fanin_fanout/README.md)