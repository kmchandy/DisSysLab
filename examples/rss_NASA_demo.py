# dsl.examples.rss_demo

import time
import json
from dsl.connectors.rss_in import RSS_In
from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
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
agent = AgentOpenAI(system_prompt=system_prompt)


def agent_op(v):
    entities = agent.fn(v["page_text"])
    entities_dict = json.loads(entities)
    v['organizations'] = entities_dict['organizations']
    v['science_terms'] = entities_dict["science_terms"]
    return {k: v.get(k) for k in ("title", "organizations", "science_terms")}


result = []


def to_result(v):
    result.append(v)


# Define the network
# g = network([(from_rss, agent_op), (agent_op, count_terms),
#             (count_terms, write_batch_per_org_csv)])
# g = network([(from_rss, agent_op), (agent_op, write_batch_per_org_csv)])
g = network([(from_rss, agent_op), (agent_op, to_result),
            (agent_op, kv_live_sink)])
g.run_network()

if __name__ == "__main__":
    print(f"result = {result}")
    for output_dict in result:
        for key, value in output_dict.items():
            print(f"{key}")
            print(f"{value}")
    print("finished")
