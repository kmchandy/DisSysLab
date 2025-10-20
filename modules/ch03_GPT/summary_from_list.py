# modules.ch03_GPT.summary_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    (
        "A play is a form of theatre that primarily consists of"
        " script between speakers and is intended for acting rather"
        " than mere reading. The writer and author of a play is"
        " known as a playwright. Plays are staged at various levels,"
        " ranging from London's West End and New York City's"
        " Broadway – the highest echelons of commercial theatre in"
        " the English-speaking world – to regional theatre, community"
        " theatre, and academic productions at universities and schools."
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


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------


system_prompt = "Summarize the text in a single line."
make_summary = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent, add result under 'summary'
# -----------------------------------------------------------


def add_summary_to_msg(msg):
    msg["summary"] = make_summary(msg["text"])
    return msg

# -----------------------------------------------------------
# 4) Sink — print
# -----------------------------------------------------------


def print_sink(msg):
    print("==============================")
    for key, value in msg.items():
        print(key)
        print(value)
        print("______________________________")
    print("")

# -----------------------------------------------------------
# 5) Connect functions and run
# -----------------------------------------------------------


g = network([(from_list_of_text, add_summary_to_msg),
            (add_summary_to_msg, print_sink)])
g.run_network()
