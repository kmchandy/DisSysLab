from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

list_of_text = [

    ("A play is a form of theatre that primarily consists of"
     "script between speakers and is intended for acting rather"
     "than mere reading. The writer and author of a play is"
     "known as a playwright. Plays are staged at various levels,"
     "ranging from London's West End and New York City's "
     "Broadway – the highest echelons of commercial theatre in"
     "the English-speaking world – to regional theatre, community"
     "theatre, and academic productions at universities and schools."
     ),
    ("Artificial general intelligence (AGI)—sometimes called human‑level"
     "intelligence AI—is a type of artificial intelligence that would"
     "match or surpass human capabilities across virtually all cognitive tasks."

     "Some researchers argue that state‑of‑the‑art large language models (LLMs)"
     "already exhibit signs of AGI‑level capability, while others maintain that"
     "genuine AGI has not yet been achieved. Beyond AGI, artificial"
     "superintelligence (ASI) would outperform the best human abilities across"
     "every domain by a wide margin."
     )
]
# Source iterator


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# Print sink


def print_sink(v):
    for key, value in v.items():
        print()
        print(key)
        print()
        print(value)
    print("")


# Create agent
system_prompt = "Summarize the text in a single line."
agent = AgentOpenAI(system_prompt=system_prompt)

# Transformer function input one value output one value


def agent_op(v):
    v["summary"] = agent.fn(v["text"])
    return v


# Create network by connecting functions
g = network([(from_list_of_text, agent_op), (agent_op, print_sink)])
g.run_network()
