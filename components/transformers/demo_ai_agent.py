# components/transformers/demo_ai_agent.py

"""
Demo AI Agent - Simulates AI agent without API calls

This module provides demo versions of AI transforms for learning and testing.
No API keys needed, no costs, instant results.

Usage:
    from components.transformers.prompts import SENTIMENT_ANALYZER
    from components.transformers.demo_ai_agent import demo_ai_agent
    
    analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
    result = analyzer("I love this!")
    # Returns: {"sentiment": "POSITIVE", "score": 0.8, "reasoning": "..."}

Swapping demo → real:
    from components.transformers.ai_agent import ai_agent
    
    analyzer = ai_agent(SENTIMENT_ANALYZER)
    # Same call, real AI instead of keyword matching
"""

from components.transformers.prompts import (
    SENTIMENT_ANALYZER,
    SPAM_DETECTOR,
    URGENCY_DETECTOR,
)

# Import demo implementations
from components.transformers.demo_sentiment import analyze_sentiment
from components.transformers.demo_spam import detect_spam
from components.transformers.demo_urgency import detect_urgency


# Mapping from prompt constants to demo functions
PROMPT_TO_FUNCTION = {
    SENTIMENT_ANALYZER: analyze_sentiment,
    SPAM_DETECTOR: detect_spam,
    URGENCY_DETECTOR: detect_urgency,
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
        >>> from components.transformers.prompts import SENTIMENT_ANALYZER
        >>> from components.transformers.demo_ai_agent import demo_ai_agent
        >>> 
        >>> analyzer = demo_ai_agent(SENTIMENT_ANALYZER)
        >>> result = analyzer("I love this!")
        >>> print(result)
        {'sentiment': 'POSITIVE', 'score': 0.8, 'reasoning': 'Contains positive words'}
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
    print("=" * 60)
    print("\nUsage:")
    print("  from components.transformers.prompts import SENTIMENT_ANALYZER")
    print("  from components.transformers.demo_ai_agent import demo_ai_agent")
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
    if result.get("is_spam") == True:
        print(f"  ✓ {result}")
        passed += 1
    else:
        print(f"  ✗ Expected is_spam=True, got: {result}")
        failed += 1

    # Test 4: Not spam
    print("Test 4: Spam detection - legitimate")
    result = fn("Python 3.13 released with performance improvements")
    if result.get("is_spam") == False:
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

    # Test 6: Unknown prompt
    print("Test 6: Unknown prompt raises ValueError")
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
