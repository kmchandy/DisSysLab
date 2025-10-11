# dsl.examples.rss_demo

import time
from dsl.connectors.rss_in import RSS_In
from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.extensions.add_fields import add_fields
from .live_kv_console import kv_live_sink

# Define functions.

rss = RSS_In(
    url="https://www.nasa.gov/feed/",
    emit_mode="item",
    batch_size=1,
    batch_seconds=4,
    fetch_page=True,
    output_keys=["title", "link", "page_text"],
    life_time=5
)


def from_rss():
    news_items = rss.run()
    for news_item in news_items:
        yield {k: news_item.get(k) for k in ("title", "page_text")}
        time.sleep(0.05)


system_prompt = '''You are an expert at extracting entities from text. 
You will be given a JSON object with keys:
- "title" (string)
- "page_text" (string)

Return exactly ONE JSON object with these keys and types:
- "title": string (copy from input)
- "organizations": array of strings. Examples: "NASA’s Deep Space Network", "European Space Agency (ESA)", "NASA Jet Propulsion Laboratory"
- "science_terms": array of strings.Examples: "Perigee", "meteors", "Constellations", "Draco", "Black holes", "Neutron Stars"

Output rules:
- Return ONLY valid RFC8259 JSON. No markdown, no code fences, no comments, no extra text.
- Use double quotes for all keys and strings.
- No trailing commas.
- If none found, use [] (empty array).
- Begin the response with "{" and end with "}".

Example output:
{"title":"Night Sky Notes","organizations":["NASA","JPL"],"science_terms":["exoplanet","spectroscopy"]}
'''
agent_extract_entitites = AgentOpenAI(system_prompt=system_prompt)


def add_entities(msg):
    return add_fields(msg, key="page_text", fn=agent_extract_entitites.fn)


g = network([(from_rss, add_entities), (add_entities, kv_live_sink)])
g.run_network()

if __name__ == "__main__":
    print("finished")
