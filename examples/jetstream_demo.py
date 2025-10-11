# examples.jetstream_demo
from dsl.extensions.agent_openai import AgentOpenAI
from dsl.extensions.add_fields import add_fields
from dsl import network
from dsl.connectors.jetstream_in import Jetstream_In
from dsl.connectors.filter_post import FilterPost
import json

# --------------------------------------------------------
#  SYSTEM PROMPTS FOR OPENAI AGENTS USED IN THIS EXAMPLE |
# ---------------------------------------------------------

# Add topics relevant to posts
topics = ["Trump", "Republican", "Democrat",
          "government", "politics", "states", "ICE", "police",
          "election", "voting", "economy", "inflation", "jobs", "unemployment",]

prompt_add_topics = f"""
You are a topic filter. Given TEXT, decide which items in TOPICS are relevant.

Output (strict JSON only):
{{"labels": ["<subset of TOPICS>"]}}

Rules:
- Consider ONLY the provided TEXT.
- Case-insensitive; include close synonyms/paraphrases.
- "labels" must be a subset of TOPICS (exact strings).
- If none are relevant, return {{"labels": []}}.
- No explanations, no extra keys.

Disambiguation:
- "states" refers to U.S. states/governance (not "state of matter" etc.).
- "ICE" refers to U.S. Immigration and Customs Enforcement.

TOPICS = {topics}

Return only JSON.
"""

# Add sentiment of posts
prompt_add_sentiment = """
You are an expert at determining the sentiment of a short text snippet.

Given TEXT, determine whether the sentiment is positive, negative, or neutral.
If positive, return 1; if negative, return -1; if neutral, return 0.

Output (strict JSON only):
{"sentiment": int}

Rules:
- Consider ONLY the provided TEXT.
- No explanations, reasoning, or extra keys.
- Do NOT include any text before or after the JSON.
- If sentiment is unclear, return 0.
- Return only valid JSON.
"""


# ----------------------------------------------------
# 1. Jetstream Input from Bluesky
# ----------------------------------------------------
jetstream = Jetstream_In(
    wanted_collections=("app.bsky.feed.post",),  # posts
    life_time=4,
    max_num_posts=100
)


def from_jetstream():
    jetstream_results = jetstream.run()
    for item in jetstream_results:
        yield item


# ----------------------------------------------------
# 2. Filter posts. Only pass posts with text length 20-2000
# and in English.
# ----------------------------------------------------

drop_posts = FilterPost(min_len=20, max_len=2000).run

# --------------------------------------------------------------------------
# 3. Filter by topics relevant to posts using LLM. Add topics to msg['labels']
# -----------------------------------------------------------------------------

agent_add_topics = AgentOpenAI(system_prompt=prompt_add_topics)


def add_topics(msg):
    return add_fields(msg, key="text", fn=agent_add_topics.fn, drop_msg=True)


# ----------------------------------------------------------------------
# 3. Add sentiment of posts using LLM. Add sentiment to msg['sentiment']
# ------------------------------------------------------------------------
agent_add_sentiment = AgentOpenAI(
    system_prompt=prompt_add_sentiment, drop_msg=False)


def add_sentiment(msg):
    return add_fields(msg, key="text", fn=agent_add_sentiment.fn)


# ----------------------------------------------------
# 4. Put results of topics and posts in list.
# ----------------------------------------------------
result = []


def to_result(v):
    text = (v.get("text") or "").strip()
    labels = v.get("labels") or []
    print(f"text =  {text}")
    print(f"labels =  {labels}")
    print(f"sentiment =  {v.get('sentiment')}")
    result.append(v)

# --------------------------------------------------------------------
# Define the network (list of edges) and run the network
# --------------------------------------------------------------------


g = network([(from_jetstream, drop_posts), (drop_posts, add_topics), (add_topics, add_sentiment),
             (add_sentiment, to_result)])
g.run_network()
