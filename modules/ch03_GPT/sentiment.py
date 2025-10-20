# modules.ch03_GPT.sentiment

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------


system_prompt = (
    "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. "
    "Give a brief reason. Return a JSON object with exactly the following format: "
    '{"sentiment_score": sentiment score, "reason": reason for the score}'
)
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent and enrich the message
# -----------------------------------------------------------


def compute_sentiment(msg):
    # Make a dict from the json str response of the agent
    sentiment_score_and_reason_json = json.loads(agent.fn(msg["text"]))
    # enrich the message by adding sentiment_score and reason fields
    msg.update(sentiment_score_and_reason_json)
    return msg

# -----------------------------------------------------------
# 4) Sink — print values
# -----------------------------------------------------------


def print_sink(msg):
    for key, val in msg.items():
        print(f"{key}:   {val}")
    print("--------------------------------")
    print()

# -----------------------------------------------------------
# 5) Connect functions and run network
# -----------------------------------------------------------


g = network([(from_list_of_text, compute_sentiment),
             (compute_sentiment, print_sink)])
g.run_network()
