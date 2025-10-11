# dsl.examples.rss_demo

from dsl.connectors.rss_in import RSS_In
from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
from .live_alert_console import live_alert_sink


# Define functions.


rss = RSS_In(url="https://api.weather.gov/alerts/active.atom",
             output_keys=["title", "link", "text"],
             emit_mode="item",
             fetch_page=True, life_time=2)  # ~2s demo


def from_rss():
    news_items = rss.run()
    for news_item in news_items:
        print(f"news_item = {news_item}")
        yield {k: news_item.get(k) for k in ("title", "page_text")}


system_prompt = '''You are a weather-alert extraction agent. 
Your job is to analyze an alert which is a dict {'title': title, 'page_text': 'page_text} where title is a short
string and page_text is a long string.
Your job is to extract information from the alert and return a JSON object 
with exactly the following keys:

"alert_type" — the official alert name (e.g., Small Craft Advisory, Flood Watch).

"location" — the human-readable city and state/territory code (e.g., Anchorage AK, Melbourne FL). 
Prefer the phrase after “by NWS …” in the title (e.g., “by NWS Anchorage AK” → Anchorage AK). If that isn’t present, use the clearest city+state mentioned in the alert text. If truly unknown, use null.

"issued_time" — the alert issuance time in UTC ISO-8601 (YYYY-MM-DDThh:mm:ssZ).

If not explicitly provided, use the most plausible end/expiration time implied by the alert; if truly unknown, use null.

"headline" — a short, natural-language headline summarizing the alert and timeframe (e.g., Small Craft Advisory until Saturday evening). Keep it under ~80 characters.

"short_advice" — one concise, practical safety tip tailored to the alert (less than 40 words, imperative mood, no exclamation marks).

Output requirements:

Return exactly one JSON object with only these five keys, in this order.

All values must be strings, except you may use null for unknown times or location.

Normalize all times to UTC with a Z suffix. Convert from offsets in the input (e.g., …-08:00 → add 8 hours).

Do not include explanations, reasoning, markdown, or extra fields.

Extraction guidance (apply in this priority):

alert_type: take the segment before “issued …” in the title; if absent, use the named event in the text (e.g., NWSheadline, event).

location: prefer the substring after by NWS at the end of the title (e.g., by NWS Anchorage AK → Anchorage AK). If multiple places are listed, pick the primary office/city associated with the NWS office. If only county/zone codes are present, choose the principal city referenced; otherwise null.

Times:

Parse all RFC 822/ISO-8601 timestamps in the title/text.

Issued: the timestamp closest to the word “issued” in the title; if not present, the earliest timestamp in the text.


headline: <Alert Type> … + concise timeframe (e.g., “until Saturday evening”, “through Sunday morning”).

short_advice: write one or two actionable sentences appropriate to the hazard (e.g., marine → “Delay small-vessel trips and check latest marine forecast.”; flood → “Avoid flooded roads; monitor updates and be ready to seek higher ground.”).

Return format example (illustrative only):
{
"alert_type": "Small Craft Advisory",
"location": "Anchorage AK",
"issued_time": "2025-10-03T11:31:00Z",
"headline": "Small Craft Advisory until Saturday evening",
"short_advice": "Delay small-vessel trips and check the latest marine forecast before departing."
}
Output rules:
- Return ONLY valid RFC8259 JSON. No markdown, no code fences, no comments, no extra text.
- Use double quotes for all keys and strings.
- No trailing commas.
- If none found, use [] (empty array).
- Begin the response with "{" and end with "}".
'''
agent = AgentOpenAI(system_prompt=system_prompt)


result = []
def to_result(v): result.append(v)


# Define the network
g = network([(from_rss, agent.fn), (agent.fn, to_result),
            (agent.fn, live_alert_sink)])
# g = network([(from_rss, to_result)])
g.run_network()

if __name__ == "__main__":
    print(f"result = {result}")
    print("finished")
