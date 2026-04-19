# gallery/ai_ml_research/demo_data.py
"""
Prepackaged articles and AI responses for the demo.
No network calls. No API key needed.
"""

ARTICLES = [
    {
        "source": "hacker_news",
        "title": "Mistral releases new open-weight model beating GPT-4 on benchmarks",
        "text": "Mistral AI has released a new open-weight language model that outperforms GPT-4 on several standard benchmarks. The model is available for download and commercial use.",
        "url": "https://news.ycombinator.com/item?id=1001",
        "timestamp": "2025-03-01T10:00:00",
    },
    {
        "source": "mit_tech_review",
        "title": "AI hiring tools shown to amplify bias in new study",
        "text": "A new study from MIT shows that AI-powered hiring tools used by Fortune 500 companies systematically disadvantage candidates from underrepresented groups, raising serious ethical concerns.",
        "url": "https://www.technologyreview.com/article/1001",
        "timestamp": "2025-03-01T11:00:00",
    },
    {
        "source": "techcrunch",
        "title": "Google DeepMind achieves breakthrough in protein folding prediction",
        "text": "DeepMind researchers have published results showing their latest model can predict protein structures with near-experimental accuracy, potentially accelerating drug discovery.",
        "url": "https://techcrunch.com/article/1001",
        "timestamp": "2025-03-01T12:00:00",
    },
    {
        "source": "venturebeat_ai",
        "title": "OpenAI raises $2B in new funding round at $80B valuation",
        "text": "OpenAI has closed a new funding round bringing its valuation to $80 billion. The capital will be used to expand compute infrastructure and accelerate research.",
        "url": "https://venturebeat.com/article/1001",
        "timestamp": "2025-03-01T13:00:00",
    },
    {
        "source": "hacker_news",
        "title": "New paper shows LLMs can self-correct reasoning errors",
        "text": "Researchers at Stanford have demonstrated that large language models can identify and correct their own reasoning errors when prompted with a structured self-review step.",
        "url": "https://news.ycombinator.com/item?id=1002",
        "timestamp": "2025-03-01T14:00:00",
    },
    {
        "source": "mit_tech_review",
        "title": "AI regulation bill passes EU Parliament with broad support",
        "text": "The European Parliament has passed landmark AI regulation requiring transparency and human oversight for high-risk AI systems. Companies have two years to comply.",
        "url": "https://www.technologyreview.com/article/1002",
        "timestamp": "2025-03-01T15:00:00",
    },
    {
        "source": "techcrunch",
        "title": "Anthropic releases Claude 4 with improved reasoning capabilities",
        "text": "Anthropic has launched Claude 4, featuring significantly improved mathematical reasoning, code generation, and multi-step problem solving compared to previous versions.",
        "url": "https://techcrunch.com/article/1002",
        "timestamp": "2025-03-01T16:00:00",
    },
    {
        "source": "venturebeat_ai",
        "title": "AI model hallucination rates drop 40% with new training technique",
        "text": "A new training technique called reinforced factuality training has reduced hallucination rates in large language models by 40% in controlled tests, researchers report.",
        "url": "https://venturebeat.com/article/1002",
        "timestamp": "2025-03-01T17:00:00",
    },
]

# Canned AI responses keyed by (prompt_keyword, article_title)
# relevance_agent responses
RELEVANCE = {
    "Mistral releases":         '{"relevant": true}',
    "AI hiring tools":          '{"relevant": true}',
    "protein folding":          '{"relevant": true}',
    "OpenAI raises":            '{"relevant": true}',
    "LLMs can self-correct":    '{"relevant": true}',
    "AI regulation bill":       '{"relevant": true}',
    "Anthropic releases":       '{"relevant": true}',
    "hallucination rates":      '{"relevant": true}',
}

SENTIMENT = {
    "Mistral releases":         '{"sentiment": "POSITIVE", "score": 0.8}',
    "AI hiring tools":          '{"sentiment": "NEGATIVE", "score": -0.7}',
    "protein folding":          '{"sentiment": "POSITIVE", "score": 0.9}',
    "OpenAI raises":            '{"sentiment": "NEUTRAL",  "score": 0.1}',
    "LLMs can self-correct":    '{"sentiment": "POSITIVE", "score": 0.7}',
    "AI regulation bill":       '{"sentiment": "NEUTRAL",  "score": 0.0}',
    "Anthropic releases":       '{"sentiment": "POSITIVE", "score": 0.8}',
    "hallucination rates":      '{"sentiment": "POSITIVE", "score": 0.6}',
}

IMPACT = {
    "Mistral releases":         '{"impact": "HIGH",   "reason": "Open-weight models shift the competitive landscape."}',
    "AI hiring tools":          '{"impact": "HIGH",   "reason": "Bias in hiring tools affects millions of job seekers."}',
    "protein folding":          '{"impact": "HIGH",   "reason": "Accelerates drug discovery for multiple diseases."}',
    "OpenAI raises":            '{"impact": "MEDIUM", "reason": "Signals continued investor confidence in AI."}',
    "LLMs can self-correct":    '{"impact": "MEDIUM", "reason": "Improves reliability of AI reasoning pipelines."}',
    "AI regulation bill":       '{"impact": "HIGH",   "reason": "Sets global precedent for AI governance."}',
    "Anthropic releases":       '{"impact": "HIGH",   "reason": "New capabilities raise the bar for AI assistants."}',
    "hallucination rates":      '{"impact": "MEDIUM", "reason": "Reduces a key reliability barrier for production AI."}',
}

REPORT = """
## Daily AI/ML Digest — Demo Edition

### HIGH IMPACT

**Mistral releases new open-weight model** (Hacker News) ✅
Open-weight models are shifting the competitive landscape away from closed APIs.

**AI hiring tools shown to amplify bias** (MIT Tech Review) ❌
Critical finding affecting millions of job seekers — expect regulatory response.

**Google DeepMind protein folding breakthrough** (TechCrunch) ✅
Significant acceleration possible for drug discovery pipelines.

**Anthropic releases Claude 4** (TechCrunch) ✅
Raises the bar for reasoning and code generation across the industry.

**EU AI regulation bill passes** (MIT Tech Review) ➖
Landmark governance moment — sets precedent other regions will follow.

### MEDIUM IMPACT

**OpenAI raises $2B** (VentureBeat) ➖
Continued capital flow into frontier AI development.

**LLMs can self-correct reasoning** (Hacker News) ✅
Promising technique for improving reliability in production systems.

**Hallucination rates drop 40%** (VentureBeat) ✅
Meaningful progress on a key barrier to enterprise AI adoption.
"""


def lookup(table, title):
    """Return canned response for the first matching key."""
    for key, value in table.items():
        if key.lower() in title.lower():
            return value
    return '{"relevant": false}'
