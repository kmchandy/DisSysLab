# components/transformers/demo_ai_agent.py

"""
Demo AI Agent - Simulates AI agent without API calls

This module provides demo versions of AI transforms for learning and testing.
No API keys needed, no costs, instant results.

Usage:
    from components.transformers.prompts import SENTIMENT_ANALYZER
    from components.transformers.demo_ai_agent import demo_ai_transform
    
    ai_function = demo_ai_transform(SENTIMENT_ANALYZER)
    result = ai_function("I love this!")
    # Returns: {"sentiment": "POSITIVE", "score": 0.8, "reasoning": "..."}
"""

from components.transformers.prompts import (
    SENTIMENT_ANALYZER,
    SPAM_DETECTOR,
    URGENCY_DETECTOR,
    EMOTION_DETECTOR,
    TONE_ANALYZER,
    TOPIC_CLASSIFIER,
    TEXT_SUMMARIZER,
)

# Import demo implementations
from components.transformers.demo_sentiment import analyze_sentiment
from components.transformers.demo_spam import detect_spam
from components.transformers.demo_urgency import detect_urgency


# Mapping from prompts to demo functions
PROMPT_TO_FUNCTION = {
    SENTIMENT_ANALYZER: analyze_sentiment,
    SPAM_DETECTOR: detect_spam,
    URGENCY_DETECTOR: detect_urgency,
    # Add more mappings as we create more demo functions
}


def demo_ai_transform(prompt: str):
    """
    Creates a demo AI transform function from a prompt.

    This simulates AI analysis using simple keyword-based logic.
    Returns the same JSON format as real AI, but uses Python rules instead.

    Args:
        prompt: Prompt string (should be one of the constants from prompts.py)

    Returns:
        Callable that takes text and returns JSON dict

    Raises:
        ValueError: If prompt is not recognized

    Example:
        >>> from components.transformers.prompts import SENTIMENT_ANALYZER
        >>> from components.transformers.demo_ai_agent import demo_ai_transform
        >>> 
        >>> analyzer = demo_ai_transform(SENTIMENT_ANALYZER)
        >>> result = analyzer("I love this!")
        >>> print(result)
        {'sentiment': 'POSITIVE', 'score': 0.8, 'reasoning': 'Contains positive words'}
    """
    # Look up the demo function for this prompt
    if prompt in PROMPT_TO_FUNCTION:
        return PROMPT_TO_FUNCTION[prompt]
    else:
        # Provide helpful error message
        available_prompts = list(PROMPT_TO_FUNCTION.keys())
        raise ValueError(
            f"No demo implementation available for this prompt.\n"
            f"Available demo prompts:\n"
            f"  - SENTIMENT_ANALYZER\n"
            f"  - SPAM_DETECTOR\n"
            f"  - URGENCY_DETECTOR\n"
            f"\nTo add more, create a demo function and add it to PROMPT_TO_FUNCTION."
        )


# Convenience function for checking what's available
def list_available_demos():
    """
    Print list of available demo transforms.

    Example:
        >>> from components.transformers.demo_ai_agent import list_available_demos
        >>> list_available_demos()
    """
    print("\n" + "=" * 60)
    print("Available Demo AI Transforms")
    print("=" * 60)

    for prompt in PROMPT_TO_FUNCTION.keys():
        # Extract prompt name from the constant
        # (This is a bit hacky but works for display)
        if prompt == SENTIMENT_ANALYZER:
            print("  ✓ SENTIMENT_ANALYZER - Analyze positive/negative/neutral sentiment")
        elif prompt == SPAM_DETECTOR:
            print("  ✓ SPAM_DETECTOR - Detect spam and promotional content")
        elif prompt == URGENCY_DETECTOR:
            print("  ✓ URGENCY_DETECTOR - Detect urgent/time-sensitive content")

    print("=" * 60)
    print("\nUsage:")
    print("  from components.transformers.prompts import SENTIMENT_ANALYZER")
    print("  from components.transformers.demo_ai_agent import demo_ai_transform")
    print("  ")
    print("  analyzer = demo_ai_transform(SENTIMENT_ANALYZER)")
    print("  result = analyzer('Your text here')")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # When run directly, show available demos
    list_available_demos()

    # Run quick test
    print("\nQuick Test:")
    print("-" * 60)

    # Test sentiment
    sentiment_fn = demo_ai_transform(SENTIMENT_ANALYZER)
    result = sentiment_fn("I love this framework!")
    print(f"Sentiment test: {result}")

    # Test spam
    spam_fn = demo_ai_transform(SPAM_DETECTOR)
    result = spam_fn("CLICK HERE for FREE MONEY!")
    print(f"Spam test: {result}")

    # Test urgency
    urgency_fn = demo_ai_transform(URGENCY_DETECTOR)
    result = urgency_fn("URGENT: System is down!")
    print(f"Urgency test: {result}")

    print("-" * 60)
