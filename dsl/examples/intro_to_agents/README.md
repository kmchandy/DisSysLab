# 🤖 Multi-Port Agents: Exploring Asynchrony and Intelligence

This section introduces **agents** — intelligent blocks with multiple inports and outports — that make decisions based on incoming messages. These examples go beyond simple pipelines to explore behaviors like **asynchrony**, **synchrony**, and **classification** using AI models.

Each agent implements a `run()` method that specifies how it reacts to incoming messages.

---

## 🟢 Example 1: Sentiment-Based Message Splitter (Asynchronous Agent)

In this example, we simulate two sources of social media posts. An agent receives posts from both sources **asynchronously** — that is, it processes messages as soon as they arrive, regardless of which input they came from.

It then classifies each message as **positive** or **negative** using a basic rule or an OpenAI-powered LLM, and routes it to the appropriate outport.

### 💡 Highlights
- Two generators → one agent with two inports
- Agent routes messages to "pos" or "neg" outports
- No need to wait for both inports — agent reacts immediately to each message

```python
from dsl.core import Agent, Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import StreamToList
from dsl.openai_utils import call_openai_chat  # make sure this is available

# Prompt-based classification using OpenAI
classification_prompt = (
    "You are an expert at analyzing social media. "
    "Label each post as 'pos' or 'neg'. Only return the label.\nPost: {msg}"
)

agent = Agent(
    inports=["in_0", "in_1"],
    outports=["pos", "neg"],
    run=lambda self: self._run()
)

def _run(self):
    while True:
        port, msg = self.receive_from_any()
        label = call_openai_chat(classification_prompt.format(msg=msg))
        label = label.strip().lower()
        if "pos" in label:
            self.send(msg, "pos")
        elif "neg" in label:
            self.send(msg, "neg")

# Attach run method to agent
agent._run = _run.__get__(agent, Agent)

net = Network(
    blocks={
        "g0": generate(["I love this!", "This is great."]),
        "g1": generate(["I hate waiting.", "This is terrible."]),
        "alpha": agent,
        "pos": StreamToList(),
        "neg": StreamToList()
    },
    connections=[
        ("g0", "out", "alpha", "in_0"),
        ("g1", "out", "alpha", "in_1"),
        ("alpha", "pos", "pos", "in"),
        ("alpha", "neg", "neg", "in")
    ]
)

net.compile_and_run()

print("✅ Positive messages:", net.blocks["pos"].saved)
print("❌ Negative messages:", net.blocks["neg"].saved)
🧠 Reflection Question
How would you modify this example if your goal was to filter spam instead of sentiment?

Suppose you want to send spam to a spam file and non-spam to a message file.

🟢 Example 2: Spam Filter Agent (Synchronous)
In this version, the agent receives a pair of messages — one from each inport — and decides whether the combined pair looks like spam. This demonstrates synchrony: the agent waits for both inputs before acting.

python
Copy
Edit
from dsl.core import Agent, Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import StreamToList

def is_spam(text):
    return "buy now" in text.lower() or "free" in text.lower()

agent = Agent(
    inports=["subject", "body"],
    outports=["spam", "message"],
    run=lambda self: self._run()
)

def _run(self):
    while True:
        subject = self.receive("subject")
        body = self.receive("body")
        full = f"{subject} {body}"
        if is_spam(full):
            self.send(full, "spam")
        else:
            self.send(full, "message")

agent._run = _run.__get__(agent, Agent)

net = Network(
    blocks={
        "sub": generate(["Win a prize!", "Meeting at noon"]),
        "body": generate(["Buy now for free!", "Let's discuss the report."]),
        "beta": agent,
        "spam": StreamToList(),
        "msg": StreamToList()
    },
    connections=[
        ("sub", "out", "beta", "subject"),
        ("body", "out", "beta", "body"),
        ("beta", "spam", "spam", "in"),
        ("beta", "message", "msg", "in")
    ]
)

net.compile_and_run()

print("🗑️ Spam messages:", net.blocks["spam"].saved)
print("📩 Legitimate messages:", net.blocks["msg"].saved)
🧠 What You Learned
You can define multi-port agents using Agent(...) and a custom run() method

Asynchronous agents act immediately when any input arrives

Synchronous agents wait for all required messages before acting

Agents can use rules, functions, or even LLMs to analyze content

You can route messages to multiple destinations using multiple outports

🚀 What’s Next?
Try building your own agents that:

Summarize multiple messages

Monitor multiple sources and alert on anomalies

Classify messages into more than two categories

See also:

dsl/examples/fan_in/ — merging multiple streams

dsl/examples/star/ — broadcasting to multiple targets

dsl/examples/gpt/ — language model blocks 