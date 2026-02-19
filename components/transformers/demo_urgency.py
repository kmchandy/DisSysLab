# components/transformers/demo_urgency.py

"""
Demo Urgency Detector - Simple keyword-based urgency detection

This is a demo implementation that uses keyword matching to detect urgency.
It returns the same JSON format as the real AI version, but uses simple Python logic.

Compare with urgency.py to see the difference between demo and real AI.
"""


def detect_urgency(text: str) -> dict:
    """
    Detects urgency using simple keyword matching.

    Returns same JSON format as real AI urgency detector.

    Args:
        text: Text to analyze

    Returns:
        Dict with:
        - text: original text (passed through)
        - urgency: "HIGH" | "MEDIUM" | "LOW"
        - metrics: dict with urgency_score (0-10), time_sensitive (bool), requires_immediate_action (bool)
        - reasoning: brief explanation

    Example:
        >>> result = detect_urgency("URGENT: System is down!")
        >>> print(result)
        {'text': '...', 'urgency': 'HIGH', 'metrics': {...}, 'reasoning': '...'}
    """
    # High urgency keywords
    high_urgency_words = [
        'urgent', 'critical', 'emergency', 'immediately', 'asap',
        'now', 'breaking', 'alert', 'crisis'
    ]

    # Medium urgency keywords
    medium_urgency_words = [
        'soon', 'today', 'quickly', 'priority', 'important',
        'deadline', 'time-sensitive', 'prompt'
    ]

    # Time-related keywords
    time_words = [
        'now', 'immediately', 'today', 'tonight', 'deadline',
        'expires', 'limited time', 'ends soon'
    ]

    # Action-required keywords
    action_words = [
        'must', 'need', 'required', 'act', 'respond', 'reply'
    ]

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Count indicators
    high_count = sum(1 for word in high_urgency_words if word in text_lower)
    medium_count = sum(
        1 for word in medium_urgency_words if word in text_lower)
    time_count = sum(1 for word in time_words if word in text_lower)
    action_count = sum(1 for word in action_words if word in text_lower)

    # Check for ALL CAPS (urgency indicator)
    words = text.split()
    all_caps_count = sum(
        1 for word in words if word.isupper() and len(word) > 2)
    caps_ratio = all_caps_count / len(words) if words else 0

    # Check for excessive punctuation
    exclamation_count = text.count('!')

    # Calculate urgency score (0-10)
    urgency_score = 0
    urgency_score += high_count * 3      # High urgency words worth 3 points each
    urgency_score += medium_count * 1.5  # Medium urgency words worth 1.5 points
    urgency_score += time_count * 1      # Time words worth 1 point
    urgency_score += action_count * 0.5  # Action words worth 0.5 points
    urgency_score += caps_ratio * 2      # ALL CAPS adds up to 2 points
    # Exclamations add up to 2 points
    urgency_score += min(exclamation_count * 0.5, 2)

    # Cap at 10
    urgency_score = min(urgency_score, 10)

    # Determine urgency level
    if urgency_score >= 4:
        urgency = "HIGH"
        reasoning = "Contains critical/urgent language"
        if high_count > 0:
            found_words = [w for w in high_urgency_words if w in text_lower]
            reasoning += f" ({', '.join(found_words[:2])})"
    elif urgency_score >= 3:
        urgency = "MEDIUM"
        reasoning = "Contains time-sensitive or priority indicators"
        if medium_count > 0:
            found_words = [w for w in medium_urgency_words if w in text_lower]
            reasoning += f" ({', '.join(found_words[:2])})"
    else:
        urgency = "LOW"
        reasoning = "No strong urgency indicators"

    # Determine flags
    time_sensitive = time_count > 0 or urgency_score >= 4
    requires_immediate_action = high_count > 0 or urgency_score >= 7

    return {
        "text": text,
        "urgency": urgency,
        "metrics": {
            "urgency_score": round(urgency_score, 1),
            "time_sensitive": time_sensitive,
            "requires_immediate_action": requires_immediate_action
        },
        "reasoning": reasoning
    }


# Example usage and testing
if __name__ == "__main__":
    print("Demo Urgency Detector - Test Cases")
    print("=" * 60)

    test_cases = [
        "URGENT: System is down! Need immediate attention!",
        "CRITICAL: Security breach detected. Act now!",
        "Please send the report by end of day today.",
        "Quick question about the meeting time.",
        "Can you review this when you get a chance?",
        "BREAKING: Major announcement coming soon!",
        "Deadline is tomorrow morning - need your input ASAP.",
        "Let me know if you have any questions."
    ]

    for text in test_cases:
        result = detect_urgency(text)
        icon = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "✓"}[result["urgency"]]
        print(f"\n{icon} Text: {text}")
        print(
            f"   Urgency: {result['urgency']} (score: {result['metrics']['urgency_score']}/10)")
        print(f"   Time-sensitive: {result['metrics']['time_sensitive']}")
        print(
            f"   Immediate action: {result['metrics']['requires_immediate_action']}")
        print(f"   Reasoning: {result['reasoning']}")

    print("\n" + "=" * 60)
