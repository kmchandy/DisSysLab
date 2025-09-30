from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# Define functions.

list_of_text = [

    ("A play is a form of theatre that primarily consists of"
     "script between speakers and is intended for acting rather"
     "than mere reading. The writer and author of a play is"
     "known as a playwright. Plays are staged at various levels,"
     "ranging from London's West End and New York City's "
     "Broadway – the highest echelons of commercial theatre in"
     "the English-speaking world – to regional theatre, community"
     "theatre, and academic productions at universities and schools."
     )
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}


results = []
def to_results(v): results.append(v)


add_key = "summary"


def agent_op(v):
    v[add_key] = agent.fn(v["text"])
    return v


system_prompt = "Summarize the text in a single line."
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
