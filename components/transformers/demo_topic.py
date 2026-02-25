# components/transformers/demo_topic.py

"""
Demo Topic Classifier — keyword-based topic classification.

Usage:
    from components.transformers.demo_topic import classify_topic

    result = classify_topic("New Python framework released for web development")
    # Returns:
    # {
    #     "primary_topic": "technology",
    #     "confidence":    0.85,
    #     "all_topics":    ["technology"],
    #     "reasoning":     "Contains technology keywords: python, framework"
    # }

This is the demo version — it uses keyword matching instead of Claude AI.
Compare with ai_agent(TOPIC_CLASSIFIER) in app_live.py to see the
demo → real pattern.
"""

# Keywords for each topic category
_TOPIC_KEYWORDS = {
    "technology": [
        "python", "javascript", "software", "programming", "code", "developer",
        "framework", "api", "database", "cloud", "ai", "machine learning",
        "algorithm", "open source", "github", "linux", "web", "app", "tech",
        "startup", "silicon valley", "computing", "cyber", "data science",
    ],
    "business": [
        "company", "startup", "revenue", "profit", "market", "investment",
        "ipo", "acquisition", "merger", "ceo", "executive", "enterprise",
        "funding", "venture", "stock", "quarterly", "earnings", "corporate",
    ],
    "science": [
        "research", "study", "scientist", "discovery", "experiment", "lab",
        "physics", "chemistry", "biology", "genome", "climate", "space",
        "nasa", "journal", "published", "hypothesis", "peer review",
    ],
    "health": [
        "health", "medical", "doctor", "patient", "hospital", "disease",
        "treatment", "drug", "vaccine", "fda", "mental health", "cancer",
        "diabetes", "clinical", "therapy", "wellness", "medicine",
    ],
    "sports": [
        "game", "team", "player", "score", "championship", "league",
        "tournament", "athlete", "coach", "season", "nba", "nfl", "soccer",
        "tennis", "olympics", "record", "win", "loss", "match",
    ],
    "entertainment": [
        "movie", "film", "music", "album", "artist", "celebrity", "netflix",
        "streaming", "award", "oscar", "grammy", "concert", "theater",
        "tv show", "series", "actor", "director", "box office",
    ],
    "politics": [
        "government", "election", "president", "congress", "senate", "vote",
        "policy", "democrat", "republican", "legislation", "law", "political",
        "minister", "parliament", "campaign", "administration", "white house",
    ],
    "education": [
        "school", "university", "student", "teacher", "course", "degree",
        "learning", "education", "tuition", "campus", "academic", "professor",
        "curriculum", "scholarship", "graduation", "college",
    ],
    "finance": [
        "bank", "loan", "interest rate", "inflation", "economy", "gdp",
        "federal reserve", "cryptocurrency", "bitcoin", "trading", "hedge fund",
        "bond", "portfolio", "financial", "mortgage", "tax", "debt",
    ],
}


def classify_topic(text: str) -> dict:
    """
    Classifies a text into a topic category using keyword matching.

    Uses keyword matching — no API key needed. Returns the same JSON
    structure as the real AI version so app.py works with either.

    Args:
        text: Article title or summary as a plain string.

    Returns:
        Dict with:
        - primary_topic: str — the best matching category
        - confidence:    float 0.0-1.0
        - all_topics:    list of matching categories
        - reasoning:     one-sentence explanation
    """
    text_lower = text.lower()

    # Count keyword hits per topic
    scores = {}
    matched_keywords = {}
    for topic, keywords in _TOPIC_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text_lower]
        if hits:
            scores[topic] = len(hits)
            matched_keywords[topic] = hits

    if not scores:
        return {
            "primary_topic": "other",
            "confidence":    0.5,
            "all_topics":    ["other"],
            "reasoning":     "No topic keywords found.",
        }

    # Sort by hit count
    sorted_topics = sorted(scores, key=scores.get, reverse=True)
    primary = sorted_topics[0]
    top_score = scores[primary]

    # Confidence based on hit count (caps at 0.95)
    confidence = min(0.95, 0.5 + top_score * 0.15)

    keywords_found = matched_keywords[primary][:3]
    reasoning = f"Contains {primary} keywords: {', '.join(keywords_found)}."

    return {
        "primary_topic": primary,
        "confidence":    round(confidence, 2),
        "all_topics":    sorted_topics,
        "reasoning":     reasoning,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Demo Topic Classifier — Test Cases")
    print("=" * 60)

    test_cases = [
        ("technology",   "New Python framework released for web development"),
        ("technology",   "GitHub launches AI code review tool"),
        ("business",     "Startup raises $50M in Series B funding round"),
        ("science",      "Researchers discover new species in Amazon rainforest"),
        ("health",       "FDA approves new cancer treatment drug"),
        ("sports",       "NBA championship game draws record TV audience"),
        ("entertainment", "New Netflix series breaks streaming records"),
        ("politics",     "Congress votes on new infrastructure legislation"),
        ("finance",      "Federal Reserve raises interest rates again"),
        ("other",        "Something completely unrelated and vague"),
    ]

    passed = 0
    for expected, text in test_cases:
        result = classify_topic(text)
        ok = result["primary_topic"] == expected
        icon = "✓" if ok else "✗"
        status = "PASS" if ok else f"FAIL (got {result['primary_topic']})"
        print(f"\n  {icon} [{expected}] {status}")
        print(f"     {text}")
        print(f"     → {result['reasoning']}")
        if ok:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_cases)} passed")
