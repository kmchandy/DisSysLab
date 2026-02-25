# components/transformers/demo_salary.py

"""
Demo Salary Extractor — regex-based salary extraction from job postings.

Usage:
    from components.transformers.demo_salary import extract_salary

    result = extract_salary("Senior Python Engineer at Stripe — Remote, $180k-$220k")
    # Returns:
    # {
    #     "salary_mentioned": True,
    #     "salary_text": "$180k-$220k",
    #     "min_salary": 180000,
    #     "max_salary": 220000
    # }

This is the demo version — it uses regex instead of Claude AI.
Compare with ai_agent(SALARY_EXTRACTOR) in app_live.py to see the
demo → real pattern.
"""

import re


def extract_salary(text: str) -> dict:
    """
    Extracts salary information from a job posting string.

    Uses regex matching — no API key needed. Returns the same JSON
    structure as the real AI version so app_extended.py works with either.

    Args:
        text: Job posting title or summary as a plain string.

    Returns:
        Dict with:
        - salary_mentioned: bool
        - salary_text:      the salary text as written, or None
        - min_salary:       integer USD/year or None
        - max_salary:       integer USD/year or None
    """
    text_lower = text.lower()

    # Match patterns like $180k, $180k-$220k, $180,000, $180k+, $200k+
    pattern = r'\$(\d+(?:,\d+)*)([kK]?)\s*(?:-\s*\$?(\d+(?:,\d+)*)([kK]?))?(\+?)'
    match = re.search(pattern, text)

    if not match:
        return {
            "salary_mentioned": False,
            "salary_text":      None,
            "min_salary":       None,
            "max_salary":       None,
        }

    # Extract the matched salary text
    salary_text = match.group(0).strip()

    def to_annual(amount_str, suffix):
        """Convert matched amount to annual USD integer."""
        amount_str = amount_str.replace(",", "")
        amount = int(amount_str)
        if suffix.lower() == "k":
            amount *= 1000
        return amount

    min_salary = to_annual(match.group(1), match.group(2))

    # If a range was matched (e.g. $180k-$220k)
    if match.group(3):
        max_salary = to_annual(match.group(3), match.group(4))
    else:
        # Single value — treat as both min and max
        max_salary = min_salary

    return {
        "salary_mentioned": True,
        "salary_text":      salary_text,
        "min_salary":       min_salary,
        "max_salary":       max_salary,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Demo Salary Extractor — Test Cases")
    print("=" * 60)

    test_cases = [
        ("Senior Python Engineer at Stripe — Remote, $180k-$220k",
         True, 180000, 220000),
        ("Staff Python Engineer at Anthropic — San Francisco, $200k-$250k",
         True, 200000, 250000),
        ("Research Scientist at Meta AI — Menlo Park, $200k+",
         True, 200000, 200000),
        ("Python Data Engineer at Spotify — NYC or Remote, $160k",
         True, 160000, 160000),
        ("ML Engineer (Python/PyTorch) at DeepMind — London or Remote",
         False, None, None),
        ("AI Researcher at Cohere — Toronto or Remote, equity + salary",
         False, None, None),
    ]

    passed = 0
    for text, exp_mentioned, exp_min, exp_max in test_cases:
        result = extract_salary(text)
        ok = (
            result["salary_mentioned"] == exp_mentioned and
            result["min_salary"] == exp_min and
            result["max_salary"] == exp_max
        )
        icon = "✓" if ok else "✗"
        status = "PASS" if ok else "FAIL"
        print(f"\n  {icon} {status}: {text[:55]}")
        print(f"     mentioned={result['salary_mentioned']}, "
              f"min={result['min_salary']}, max={result['max_salary']}")
        if ok:
            passed += 1

    print()
    print(f"Results: {passed}/{len(test_cases)} passed")
