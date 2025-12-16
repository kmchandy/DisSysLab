# modules.ch03_GPT.entities_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi.",
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]

system_prompt = (
    "Your task is to read the input text and extract entities"
    "such as names of people, organizations, countries and locations."
    "Return a JSON array of the entities found in the text where the key is"
    " the type of entity (e.g., Person, Organization, Location) and the value"
    "is the list of entities of that type. For example"
    '{"Person": ["Obama", "Modi"], "Location": ["USA", "New Delhi"]}'
)


source = source_list_of_text(list_of_text)
ai_agent = AgentOpenAI(system_prompt=system_prompt)

g = network([(source.run, ai_agent.enrich_dict),
             (ai_agent.enrich_dict, kv_live_sink)])
g.run_network()
