from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.connectors.live_kv_console import kv_live_sink
# Define functions.

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi."
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}


def print_sink(v):
    print('==============================')
    for key, value in v.items():
        print(key)
        print(value)
        print('______________________________')
    print('')


system_prompt = "Extract entities."
agent = AgentOpenAI(system_prompt=system_prompt)


def agent_op(v):
    v['entities'] = agent.fn(v["text"])
    return v


g = network([(from_list_of_text, agent_op), (agent_op, print_sink)])
g.run_network()
