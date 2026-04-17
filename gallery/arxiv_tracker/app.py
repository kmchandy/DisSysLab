# ============================================================
# arXiv Research Tracker
# Monitors three arXiv subject feeds for new papers.
#
# Configurable: edit TOPICS below to focus on papers you care about.
# The app filters all incoming papers and keeps only those that
# match your topics, then classifies each by type and impact.
#
# Topology:
#   arxiv_cs_ai ─┐
#   arxiv_cs_lg  ┼→ topic_filter → classify → impact → ┬→ display
#   arxiv_cs_cl ─┘                                      └→ batcher → report
#                                           clock ───────┘
#
# Sources: arxiv.org/list/cs.AI, cs.LG, cs.CL (updated daily by arXiv)
# Polling: every hour — duplicate papers are filtered automatically
# ============================================================

import json
import re
from dissyslab import network
from dissyslab.blocks import Source, Transform, Sink
from dissyslab.components.sources.web_scraper import arxiv_cs_ai, arxiv_cs_lg, arxiv_cs_cl
from dissyslab.components.transformers.ai_agent import ai_agent
from dissyslab.components.transformers.stateful_agent import StatefulAgent
from dissyslab.components.sources.clock_source import ClockSource

# ── Configuration ─────────────────────────────────────────────
# Edit this list to focus on papers that interest you.
# Papers not matching any topic are filtered out before AI analysis.

TOPICS = [
    "large language models",
    "agents and multi-agent systems",
    "reinforcement learning",
    "distributed systems",
    "AI safety and alignment",
]

# ── Sources ───────────────────────────────────────────────────
ai_feed = arxiv_cs_ai(max_articles=30, poll_interval=3600)
lg_feed = arxiv_cs_lg(max_articles=30, poll_interval=3600)
cl_feed = arxiv_cs_cl(max_articles=30, poll_interval=3600)

ai_source = Source(fn=ai_feed.run, name="arxiv_cs_ai")
lg_source = Source(fn=lg_feed.run, name="arxiv_cs_lg")
cl_source = Source(fn=cl_feed.run, name="arxiv_cs_cl")

# ── AI Agents ─────────────────────────────────────────────────
topics_str = "\n".join(f"  - {t}" for t in TOPICS)

relevance_agent = ai_agent(f"""
    Does this paper relate to any of the following topics?
{topics_str}
    Consider the title, authors, and subjects carefully.
    Return JSON only, no explanation: {{"relevant": true or false}}
""")

classify_agent = ai_agent("""
    What type of research paper is this?
    Return JSON only, no explanation:
    {{"type": "EMPIRICAL" | "THEORETICAL" | "SURVEY" | "BENCHMARK" | "SYSTEM" | "OTHER",
      "topic": "one short phrase describing the main topic (5 words max)"}}
""")

impact_agent = ai_agent("""
    How significant is this paper likely to be for the field?
    Consider novelty, scope, and practical applicability.
    Return JSON only, no explanation:
    {{"impact": "HIGH" | "MEDIUM" | "LOW",
      "reason": "one sentence"}}
""")

reporter_agent = ai_agent(f"""
    You receive a JSON batch of arXiv papers grouped by source in by_source.
    Write a daily research digest covering these topics:
{topics_str}
    For each source (cs.AI, cs.LG, cs.CL), list the HIGH impact papers first,
    then MEDIUM. For each paper include: title, type, topic, and one-sentence
    reason for its significance. End with a brief cross-source summary of
    today's most important themes.
    Return plain text, not JSON.
""")

# ── Helper ────────────────────────────────────────────────────


def _parse_json(raw):
    """Extract JSON from Claude response, tolerating extra text or pre-parsed dict."""
    if isinstance(raw, dict):
        return raw
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    return json.loads(match.group()) if match else {}


# ── Transform Functions ───────────────────────────────────────


def filter_relevant(paper):
    if not paper.get("text", "").strip():
        return None
    result = _parse_json(relevance_agent(paper["text"]))
    if not result.get("relevant"):
        return None
    return paper


def classify_paper(paper):
    result = _parse_json(classify_agent(paper["text"]))
    paper["type"] = result.get("type", "OTHER")
    paper["topic"] = result.get("topic", "")
    return paper


def rate_impact(paper):
    result = _parse_json(impact_agent(paper["text"]))
    paper["impact"] = result.get("impact", "LOW")
    paper["reason"] = result.get("reason", "")
    return paper


def display(paper):
    impact_icons = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
    type_icons = {
        "EMPIRICAL":   "🔬",
        "THEORETICAL": "📐",
        "SURVEY":      "📚",
        "BENCHMARK":   "📊",
        "SYSTEM":      "⚙️ ",
        "OTHER":       "📄",
    }
    impact_icon = impact_icons.get(paper["impact"], "?")
    type_icon = type_icons.get(paper["type"], "📄")
    source = paper["source"].replace("arxiv_", "").upper()
    topic = paper.get("topic", "")

    authors = ""
    for line in paper.get("text", "").splitlines():
        if line.startswith("Authors:"):
            authors = line.replace("Authors:", "").strip()
            break
    if len(authors) > 80:
        truncated = authors[:80].rsplit(",", 1)[0]
        authors = truncated + "..."

    print(f"{impact_icon}{type_icon} [{source:>8}] {topic}")
    print(f"     {paper['title']}")
    print(f"     👤 {authors}")
    print(f"     💬 {paper['reason']}")
    print(f"     🔗 {paper['url']}")
    print()


def write_report(batch):
    return {"report": reporter_agent(json.dumps(batch, indent=2))}


def print_report(msg):
    print("\n" + "=" * 70)
    print("DAILY ARXIV RESEARCH DIGEST")
    print("=" * 70)
    print(msg["report"])
    print("=" * 70 + "\n")


# ── Batch Reporting ───────────────────────────────────────────
batcher = StatefulAgent(max_articles=300, clear_on_tick=True)
clock = ClockSource.daily()

# ── Build Nodes ───────────────────────────────────────────────
topic_filter = Transform(fn=filter_relevant, name="topic_filter")
classify = Transform(fn=classify_paper,  name="classify")
impact = Transform(fn=rate_impact,     name="impact")
display_sink = Sink(fn=display,              name="display")
batcher_node = Transform(fn=batcher.run,     name="batcher")
clock_source = Source(fn=clock.run,          name="clock")
report_node = Transform(fn=write_report,    name="report_writer")
report_sink = Sink(fn=print_report,         name="report_sink")

# ── Network ───────────────────────────────────────────────────
g = network([
    (ai_source,  topic_filter),
    (lg_source,  topic_filter),
    (cl_source,  topic_filter),

    (topic_filter, classify),
    (classify,     impact),

    (impact,      display_sink),
    (impact,      batcher_node),

    (clock_source, batcher_node),
    (batcher_node, report_node),
    (report_node,  report_sink),
])

if __name__ == "__main__":
    print("\n📄 arXiv Research Tracker")
    print(f"   Sources: cs.AI, cs.LG, cs.CL (polling hourly)")
    print(f"   Topics: {', '.join(TOPICS)}")
    print("   Streaming matching papers to console. Daily digest at midnight.")
    print("   Press Ctrl+C to stop.\n")
    g.run_network(timeout=None)
