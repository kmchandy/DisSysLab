from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# Define functions.

list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}


def print_sink(v): return v


add_key = "sentiment"


def agent_op(v):
    v[add_key] = agent.fn(v["text"])
    return v


system_prompt = "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. Give a brief reason."
agent = AgentOpenAI(system_prompt=system_prompt)

# Define the graph
g = network([(from_list_of_text, agent_op), (agent_op, print_sink)])
g.run_network()
