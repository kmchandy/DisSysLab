# components/transformers/demo_jobs.py

"""
Demo Jobs — keyword-based job relevance matching.

Usage:
    from dissyslab.components.transformers.demo_jobs import check_job_relevance

    result = check_job_relevance("Senior Python Engineer at Stripe — Remote, $180k")
    # Returns:
    # {
    #     "match":      "STRONG" | "PARTIAL" | "NONE",
    #     "confidence": 0.0-1.0,
    #     "reason":     "one sentence explanation"
    # }

This is the demo version — it uses keyword matching instead of Claude AI.
Compare with ai_agent(JOB_DETECTOR) in app_live.py to see the demo → real pattern.

The real version uses JOB_DETECTOR from prompts.py — a prompt that describes
the target role in plain English. Change that prompt to personalize the monitor.
The rest of the app stays exactly the same.
"""

# Keywords that suggest a strong Python/ML engineering match
_STRONG_MATCH_KEYWORDS = [
    "senior python", "staff python", "principal python",
    "ml engineer", "machine learning engineer",
    "ai engineer", "ai researcher",
    "distributed systems", "data engineer",
]

# Keywords that suggest a partial match
_PARTIAL_MATCH_KEYWORDS = [
    "python", "pytorch", "tensorflow", "nlp", "llm",
    "backend", "data scientist", "remote", "api",
]

# Keywords that suggest it's not a match (wrong language, on-site only, junior)
_NO_MATCH_KEYWORDS = [
    "java ", "ruby ", "php ", "c++ ", ".net ",
    "on-site only", "on site only", "no remote",
    "junior", "unpaid", "part time",
]

# Keywords that suggest spam (should have been filtered, but just in case)
_SPAM_KEYWORDS = [
    "click here", "free money", "guaranteed income",
    "get rich", "buy now", "passive income", "make $",
    "work from home guaranteed", "no experience needed",
]


def check_job_relevance(text: str) -> dict:
    """
    Checks whether a job posting matches a target Python/ML engineering role.

    Uses keyword matching — no API key needed. Returns the same JSON
    structure as the real AI version so app.py works with either.

    Args:
        text: Job posting title or summary as a plain string.

    Returns:
        Dict with:
        - match:      "STRONG" | "PARTIAL" | "NONE"
        - confidence: float 0.0-1.0
        - reason:     one-sentence explanation
    """
    text_lower = text.lower()

    # Spam that slipped through — treat as no match
    if any(kw in text_lower for kw in _SPAM_KEYWORDS):
        return {
            "match":      "NONE",
            "confidence": 0.9,
            "reason":     "Appears to be spam or misleading posting."
        }

    # Explicit disqualifiers
    if any(kw in text_lower for kw in _NO_MATCH_KEYWORDS):
        return {
            "match":      "NONE",
            "confidence": 0.8,
            "reason":     "Role requires wrong language, on-site only, or junior level."
        }

    # Strong match
    if any(kw in text_lower for kw in _STRONG_MATCH_KEYWORDS):
        return {
            "match":      "STRONG",
            "confidence": 0.85,
            "reason":     "Matches target role: senior Python or ML engineer."
        }

    # Partial match
    if any(kw in text_lower for kw in _PARTIAL_MATCH_KEYWORDS):
        return {
            "match":      "PARTIAL",
            "confidence": 0.6,
            "reason":     "Partial match: relevant technology but role level unclear."
        }

    # No match
    return {
        "match":      "NONE",
        "confidence": 0.7,
        "reason":     "No relevant keywords found for target role."
    }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Demo Jobs — Test Cases")
    print("=" * 60)

    test_cases = [
        ("STRONG",  "Senior Python Engineer at Stripe — Remote, $180k-$220k"),
        ("STRONG",  "ML Engineer (Python/PyTorch) at DeepMind — London or Remote"),
        ("STRONG",  "Staff Python Engineer at Anthropic — San Francisco, $200k-$250k"),
        ("PARTIAL", "Data Scientist (Python/SQL) at Airbnb — Remote, $165k"),
        ("PARTIAL", "Python API Developer at Twilio — Remote-friendly, $140k"),
        ("NONE",    "Java Developer at Oracle — Austin TX, on-site required"),
        ("NONE",    "Junior Python Developer at local agency — part time, unpaid trial"),
        ("NONE",    "CLICK HERE to get rich quick — work from home guaranteed!!!"),
        ("NONE",    "C++ Systems Engineer at NVIDIA — Santa Clara"),
    ]

    passed = 0
    for expected, text in test_cases:
        result = check_job_relevance(text)
        icon = "✓" if result["match"] == expected else "✗"
        status = "PASS" if result["match"] == expected else f"FAIL (got {result['match']})"
        print(f"\n  {icon} [{expected}] {status}")
        print(f"     {text[:60]}")
        print(f"     → {result['reason']}")
        if result["match"] == expected:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_cases)} passed")
