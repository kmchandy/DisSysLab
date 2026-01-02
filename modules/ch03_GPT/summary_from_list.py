# modules.ch03_GPT.summary_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text

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

system_prompt = (
    "Return a JSON document {'summary': x}"
    "where x is a summary of the input text."
)

source = source_list_of_text(list_of_text)
ai_agent = AgentOpenAI(system_prompt=system_prompt)

g = network([(source.run, ai_agent.enrich_dict),
             (ai_agent.enrich_dict, kv_live_sink)])
g.run_network()
