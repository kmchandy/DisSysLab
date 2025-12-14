# modules.ch03_openai.entities_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text
from .ai_simple_demo import ai_simple_demo


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

ai_simple_demo(list_of_text, system_prompt)
