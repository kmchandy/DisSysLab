# modules.ch03_GPT.sentiment

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

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
    "Give a brief reason."
)
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent, add result under add_key
# -----------------------------------------------------------

add_key = "sentiment"   # field name to write into the dict


def agent_op(v):
    v[add_key] = agent.fn(v["text"])
    return v

# -----------------------------------------------------------
# 4) Sink — print values
# -----------------------------------------------------------


def print_sink(v):
    print(v)
    print("--------------------------------")
    print()


# -----------------------------------------------------------
# 5) Connect functions and run network
# -----------------------------------------------------------


g = network([(from_list_of_text, agent_op), (agent_op, print_sink)])
g.run_network()
