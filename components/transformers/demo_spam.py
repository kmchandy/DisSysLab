# components/transformers/demo_spam.py

"""
Demo Spam Detector - Simple keyword-based spam detection

This is a demo implementation that uses keyword matching to detect spam.
It returns the same JSON format as the real AI version, but uses simple Python logic.

Compare with spam.py to see the difference between demo and real AI.
"""


def detect_spam(text: str) -> dict:
    """
    Detects spam using simple keyword matching.

    Returns same JSON format as real AI spam detector.

    Args:
        text: Text to analyze

    Returns:
        Dict with:
        - text: original text (passed through)
        - is_spam: bool (True if spam detected)
        - confidence: float from 0.0 to 1.0
        - spam_type: "promotional" | "phishing" | "scam" | "legitimate"
        - reason: brief explanation

    Example:
        >>> result = detect_spam("CLICK HERE for FREE MONEY!")
        >>> print(result)
        {'text': '...', 'is_spam': True, 'confidence': 0.95, 'spam_type': 'promotional', 'reason': '...'}
    """
    # Spam indicator keywords
    spam_keywords = [
        'click here', 'buy now', 'limited time', 'act now',
        'free money', 'winner', 'congratulations', 'claim',
        'urgent offer', 'exclusive deal', 'special promotion'
    ]

    # Phishing indicators
    phishing_keywords = [
        'verify account', 'confirm identity', 'reset password',
        'account suspended', 'unusual activity', 'click link'
    ]

    # Scam indicators
    scam_keywords = [
        'lottery', 'inheritance', 'prince', 'million dollars',
        'wire transfer', 'bank account', 'social security'
    ]

    # Convert to lowercase for matching
    text_lower = text.lower()

    # Count indicators
    spam_count = sum(1 for keyword in spam_keywords if keyword in text_lower)
    phishing_count = sum(
        1 for keyword in phishing_keywords if keyword in text_lower)
    scam_count = sum(1 for keyword in scam_keywords if keyword in text_lower)

    # Check for ALL CAPS (spam indicator)
    words = text.split()
    all_caps_count = sum(
        1 for word in words if word.isupper() and len(word) > 2)
    caps_ratio = all_caps_count / len(words) if words else 0

    # Check for excessive punctuation
    exclamation_count = text.count('!')

    # Calculate spam score
    total_indicators = spam_count + phishing_count + scam_count

    # Determine spam type and confidence
    if scam_count > 0:
        is_spam = True
        spam_type = "scam"
        confidence = min(0.7 + (scam_count * 0.15), 1.0)
        reason = "Contains scam indicators"

    elif phishing_count > 0:
        is_spam = True
        spam_type = "phishing"
        confidence = min(0.7 + (phishing_count * 0.15), 1.0)
        reason = "Contains phishing indicators"

    elif spam_count >= 2 or (spam_count >= 1 and caps_ratio > 0.3):
        is_spam = True
        spam_type = "promotional"
        confidence = min(0.6 + (spam_count * 0.15) + (caps_ratio * 0.2), 1.0)
        reason = "Contains promotional language and urgency tactics"

    elif spam_count == 1 or exclamation_count >= 3:
        is_spam = True
        spam_type = "promotional"
        confidence = 0.6
        reason = "Mildly promotional content"

    else:
        is_spam = False
        spam_type = "legitimate"
        confidence = 0.1
        reason = "No significant spam indicators detected"

    return {
        "text": text,
        "is_spam": is_spam,
        "confidence": round(confidence, 2),
        "spam_type": spam_type,
        "reason": reason
    }


# Example usage and testing
if __name__ == "__main__":
    print("Demo Spam Detector - Test Cases")
    print("=" * 60)

    test_cases = [
        "CLICK HERE for FREE MONEY! Limited time offer!",
        "Your account has been suspended. Click link to verify.",
        "You've won the lottery! Claim your million dollars now!",
        "BUY NOW! Special promotion ends today!",
        "Hey, can we schedule a meeting for tomorrow?",
        "Please send me the report when you get a chance.",
        "URGENT: Act now or miss out!",
        "Great presentation today, thanks for sharing."
    ]

    for text in test_cases:
        result = detect_spam(text)
        icon = "🚫" if result["is_spam"] else "✓"
        print(f"\n{icon} Text: {text}")
        print(
            f"   Spam: {result['is_spam']} (confidence: {result['confidence']})")
        print(f"   Type: {result['spam_type']}")
        print(f"   Reason: {result['reason']}")

    print("\n" + "=" * 60)
