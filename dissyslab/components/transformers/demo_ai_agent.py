# dissyslab/components/transformers/demo_ai_agent.py

"""
Demo AI Agent - Simulates AI agent without API calls

This module provides demo versions of AI transforms for learning and testing.
No API keys needed, no costs, instant results.

Usage:
    from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
    from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent

    analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
    result = analyzer("I love this!")
    # Returns: {"sentiment": "POSITIVE", "score": 0.8, "reasoning": "..."}

Swapping demo → real:
    from dissyslab.components.transformers.ai_agent import ai_agent

    analyzer = ai_agent(SENTIMENT_ANALYZER)
    # Same call, real AI instead of keyword matching
"""

from dissyslab.components.transformers.prompts import (
    TOPIC_CLASSIFIER,
    SENTIMENT_ANALYZER,
    SPAM_DETECTOR,
    URGENCY_DETECTOR,
    JOB_DETECTOR,
    SALARY_EXTRACTOR,
)

# Import demo implementations
from dissyslab.components.transformers.demo_sentiment import analyze_sentiment
from dissyslab.components.transformers.demo_spam import detect_spam
from dissyslab.components.transformers.demo_urgency import detect_urgency
from dissyslab.components.transformers.demo_jobs import check_job_relevance
from dissyslab.components.transformers.demo_salary import extract_salary
from dissyslab.components.transformers.demo_topic import classify_topic

# Mapping from prompt constants to demo functions
PROMPT_TO_FUNCTION = {
    SENTIMENT_ANALYZER: analyze_sentiment,
    SPAM_DETECTOR:      detect_spam,
    URGENCY_DETECTOR:   detect_urgency,
    JOB_DETECTOR:       check_job_relevance,
    SALARY_EXTRACTOR:   extract_salary,
    TOPIC_CLASSIFIER:   classify_topic,
}


def demo_ai_agent(prompt: str):
    """
    Creates a demo AI transform function from a prompt.

    This simulates AI analysis using simple keyword-based logic.
    Returns the same JSON format as real AI, but uses Python rules instead.

    Args:
        prompt: Prompt constant from prompts.py (e.g. SENTIMENT_ANALYZER)

    Returns:
        Callable that takes text and returns JSON dict

    Raises:
        ValueError: If prompt is not recognized

    Example:
        >>> from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER
        >>> from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent
        >>>
        >>> analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        >>> result = analyzer("I love this!")
        >>> print(result)
        {'sentiment': 'POSITIVE', 'score': 0.8,
            'reasoning': 'Contains positive words'}
    """
    if prompt in PROMPT_TO_FUNCTION:
        return PROMPT_TO_FUNCTION[prompt]
    else:
        raise ValueError(
            f"No demo implementation available for this prompt.\n"
            f"Available demo prompts:\n"
            f"  - SENTIMENT_ANALYZER\n"
            f"  - SPAM_DETECTOR\n"
            f"  - URGENCY_DETECTOR\n"
            f"  - JOB_DETECTOR\n"
            f"  - SALARY_EXTRACTOR\n"
            f"  - TOPIC_CLASSIFIER\n"
            f"\nTo add more, create a demo function and add it to PROMPT_TO_FUNCTION."
        )


def list_available_demos():
    """Print list of available demo transforms."""
    print("\n" + "=" * 60)
    print("Available Demo AI Agents")
    print("=" * 60)
    print("  ✓ SENTIMENT_ANALYZER - Positive/negative/neutral")
    print("  ✓ SPAM_DETECTOR      - Spam detection")
    print("  ✓ URGENCY_DETECTOR   - Urgency detection")
    print("  ✓ JOB_DETECTOR       - Job relevance matching")
    print("  ✓ SALARY_EXTRACTOR   - Salary extraction")
    print("  ✓ TOPIC_CLASSIFIER   - Topic classification")
    print("=" * 60)
    print("\nUsage:")
    print("  from dissyslab.components.transformers.prompts import SENTIMENT_ANALYZER")
    print("  from dissyslab.components.transformers.demo_ai_agent import demo_ai_agent")
    print("  ")
    print("  analyzer = demo_ai_agent(SENTIMENT_ANALYZER)")
    print("  result = analyzer('Your text here')")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    list_available_demos()

    passed = 0
    failed = 0

    # Test 1: Positive sentiment
    print("Test 1: Positive sentiment")
    fn = demo_ai_agent(SENTIMENT_ANALYZER)
    result = fn("I love this framework!")
    if result.get("sentiment") == "POSITIVE":
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected POSITIVE, got: {result}")
        failed += 1

    # Test 2: Negative sentiment
    print("Test 2: Negative sentiment")
    result = fn("This is terrible and I hate it")
    if result.get("sentiment") == "NEGATIVE":
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected NEGATIVE, got: {result}")
        failed += 1

    # Test 3: Spam detected
    print("Test 3: Spam detection - spam")
    fn = demo_ai_agent(SPAM_DETECTOR)
    result = fn("CLICK HERE for FREE MONEY!")
    if result.get("is_spam") is True:
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected is_spam=True, got: {result}")
        failed += 1

    # Test 4: Not spam
    print("Test 4: Spam detection - legitimate")
    result = fn("Python 3.13 released with performance improvements")
    if result.get("is_spam") is False:
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected is_spam=False, got: {result}")
        failed += 1

    # Test 5: Urgency
    print("Test 5: Urgency detection")
    fn = demo_ai_agent(URGENCY_DETECTOR)
    result = fn("URGENT: System is down!")
    if result.get("urgency") == "HIGH":
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected HIGH, got: {result}")
        failed += 1

    # Test 6: Job detector - strong match
    print("Test 6: Job detector - strong match")
    fn = demo_ai_agent(JOB_DETECTOR)
    result = fn("Senior Python Engineer at Stripe — Remote, $180k")
    if result.get("match") in ("STRONG", "PARTIAL"):
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected STRONG or PARTIAL, got: {result}")
        failed += 1

    # Test 7: Job detector - no match
    print("Test 7: Job detector - no match")
    result = fn("Java Developer at Oracle — Austin TX, on-site required")
    if result.get("match") == "NONE":
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected NONE, got: {result}")
        failed += 1

    # Test 8: Salary extractor - with salary
    print("Test 8: Salary extractor - salary present")
    fn = demo_ai_agent(SALARY_EXTRACTOR)
    result = fn("Senior Python Engineer at Stripe — Remote, $180k-$220k")
    if result.get("salary_mentioned") is True and result.get("min_salary") == 180000:
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected salary_mentioned=True, min=180000, got: {result}")
        failed += 1

    # Test 9: Salary extractor - no salary
    print("Test 9: Salary extractor - no salary")
    result = fn("ML Engineer at DeepMind — London or Remote")
    if result.get("salary_mentioned") is False:
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected salary_mentioned=False, got: {result}")
        failed += 1

    # Test 10: Unknown prompt
    print("Test 10: Unknown prompt raises ValueError")
    try:
        demo_ai_agent("not a real prompt")
        print("  ✗ Should have raised ValueError")
        failed += 1
    except ValueError:
        print("  ✓ ValueError raised")
        passed += 1

    print(f"\nResults: {passed}/{passed + failed} tests passed")
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
