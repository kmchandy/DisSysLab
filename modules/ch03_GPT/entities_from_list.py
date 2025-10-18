# modules.ch03_openai.entities_from_list

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json

# -----------------------------------------------------------
# 1) Source — yield dicts with a "text" field
# -----------------------------------------------------------

list_of_text = [
    "Obama was the first African American president of the USA.",
    "The capital of India is New Delhi and its Prime Minister is Narendra Modi.",
    "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}

# -----------------------------------------------------------
# 2) OpenAI agent — provide a system prompt
# -----------------------------------------------------------


system_prompt = (
    "Your task is to read the input text and extract entities"
    "such as names of people, organizations, countries and locations."
    "Return a JSON array of the entities found in the text where the key is"
    " the type of entity (e.g., Person, Organization, Location) and the value"
    "is the list of entities of that type. For example"
    '{"Person": ["Obama", "Modi"], "Location": ["USA", "New Delhi"]}'
)
agent = AgentOpenAI(system_prompt=system_prompt)

# -----------------------------------------------------------
# 3) Transformer — call the agent, add result under 'entities'
# -----------------------------------------------------------


def add_entities_to_msg(msg):
    # Make a dict from the json str response of the agent
    entities = json.loads(agent.fn(msg["text"]))
    # enrich the message by adding sentiment_score and reason fields
    msg.update(entities)
    return msg


# -----------------------------------------------------------
# 4) Sink — pretty print dict keys/values
# -----------------------------------------------------------


def print_sink(v):
    print("==============================")
    for key, value in v.items():
        print(key)
        print(value)
        print("______________________________")
    print("")

# -----------------------------------------------------------
# 5) Connect functions and run
# -----------------------------------------------------------


g = network([(from_list_of_text, add_entities_to_msg),
             (add_entities_to_msg, print_sink)])
g.run_network()
