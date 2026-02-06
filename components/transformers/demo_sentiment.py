# components/transformers/demo_sentiment.py

"""
Demo Sentiment Analyzer - Simple keyword-based sentiment analysis

This is a demo implementation that uses keyword matching to analyze sentiment.
It returns the same JSON format as the real AI version, but uses simple Python logic.

Compare with sentiment.py to see the difference between demo and real AI.
"""


def analyze_sentiment(text: str) -> dict:
    """
    Analyzes sentiment using simple keyword matching.

    Returns same JSON format as real AI sentiment analyzer.

    Args:
        text: Text to analyze

    Returns:
        Dict with:
        - sentiment: "POSITIVE" | "NEGATIVE" | "NEUTRAL"
        - score: float from -1.0 (very negative) to +1.0 (very positive)
        - reasoning: brief explanation

    Example:
        >>> result = analyze_sentiment("I love this!")
        >>> print(result)
        {'sentiment': 'POSITIVE', 'score': 0.8, 'reasoning': 'Contains positive words: love'}
    """
    # Simple keyword lists
    positive_words = [
        'love', 'great', 'excellent', 'amazing', 'wonderful',
        'fantastic', 'best', 'awesome', 'perfect', 'happy',
        'excited', 'brilliant', 'outstanding', 'superb'
    ]

    negative_words = [
        'hate', 'terrible', 'awful', 'horrible', 'worst',
        'bad', 'poor', 'disappointing', 'frustrated', 'angry',
        'annoyed', 'upset', 'sad', 'disappointed'
    ]

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Count positive and negative words
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    # Determine sentiment
    if pos_count > neg_count:
        sentiment = "POSITIVE"
        score = min(0.5 + (pos_count * 0.2), 1.0)  # 0.5 to 1.0
        found_words = [w for w in positive_words if w in text_lower]
        reasoning = f"Contains positive words: {', '.join(found_words[:3])}"

    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
        score = max(-0.5 - (neg_count * 0.2), -1.0)  # -0.5 to -1.0
        found_words = [w for w in negative_words if w in text_lower]
        reasoning = f"Contains negative words: {', '.join(found_words[:3])}"

    else:
        sentiment = "NEUTRAL"
        score = 0.0
        reasoning = "No strong positive or negative indicators"

    return {
        "text": text,
        "sentiment": sentiment,
        "score": round(score, 2),
        "reasoning": reasoning
    }


# Example usage and testing
if __name__ == "__main__":
    print("Demo Sentiment Analyzer - Test Cases")
    print("=" * 60)

    test_cases = [
        "I love this framework! It's amazing!",
        "This is terrible and disappointing.",
        "The meeting is scheduled for tomorrow.",
        "Great job on the project!",
        "I hate this awful experience.",
        "Please send the report by Friday."
    ]

    for text in test_cases:
        result = analyze_sentiment(text)
        icon = {"POSITIVE": "😊", "NEGATIVE": "😞",
                "NEUTRAL": "😐"}[result["sentiment"]]
        print(f"\n{icon} Text: {text}")
        print(
            f"   Sentiment: {result['sentiment']} (score: {result['score']})")
        print(f"   Reasoning: {result['reasoning']}")

    print("\n" + "=" * 60)
