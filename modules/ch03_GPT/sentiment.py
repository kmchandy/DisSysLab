# modules.ch03_GPT.sentiment

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json
from dsl.connectors.live_kv_console import kv_live_sink

# -----------------------------------------------------------
#  Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

# Iterator of a stream of messages where each message is a dict
# with a "text" field which is an item from list_of_text


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
#  Creat OpenAI agent by providing a system prompt
# -----------------------------------------------------------


system_prompt = (
    "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. "
    "Give a brief reason. Return a JSON object with exactly the following format: "
    '{"sentiment_score": sentiment score, "reason": reason for the score}'
)
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
#  Transformer — call the agent and enrich the message
# -----------------------------------------------------------


def compute_sentiment(msg):
    # msg is a dict with a "text" field
    # Make a dict from the json str response of the agent
    sentiment_score_and_reason_json = json.loads(agent.run(msg["text"]))
    # enrich the message by adding sentiment_score and reason fields
    msg.update(sentiment_score_and_reason_json)
    return msg


# -----------------------------------------------------------
#  Connect functions and run network
# -----------------------------------------------------------
g = network([(from_list_of_text, compute_sentiment),
             (compute_sentiment, kv_live_sink)])
g.run_network()
