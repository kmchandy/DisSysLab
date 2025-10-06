from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# Define functions.

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi."
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}


results = []
def to_results(v): results.append(v)


add_key = "entities"


def agent_op(v):
    v[add_key] = agent.fn(v["text"])
    return v


system_prompt = "Extract entities."
agent = AgentOpenAI(system_prompt=system_prompt)

# Define the graph
g = network([(from_list_of_text, agent_op), (agent_op, to_results)])
g.run_network()

if __name__ == "__main__":
    for result in results:
        for key, value in result.items():
            print(key)
            print(value)
        print("")
