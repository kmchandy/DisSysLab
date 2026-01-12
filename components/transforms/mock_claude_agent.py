# components/transforms/mock_claude_agent.py

"""
MockClaudeAgent: Keyword-based analysis that simulates AI.

This is the mock version of ClaudeAgent used in Module 2 (basic examples).
It has the exact same interface as ClaudeAgent but uses simple keyword matching
instead of calling the Claude API.

In Module 9, students replace this with the real ClaudeAgent.
"""

from typing import Dict, Any


class MockClaudeAgent:
    """
    Mock AI agent that uses keyword matching instead of Claude API.

    This mirrors the ClaudeAgent interface exactly, making it easy to swap
    mock → real when students progress from Module 2 to Module 9.

    Example:
        >>> from components.transforms import MockClaudeAgent
        >>> spam_detector = MockClaudeAgent(task="spam_detection")
        >>> result = spam_detector.run("Click here for FREE MONEY!")
        >>> print(result)
        {'is_spam': True, 'confidence': 0.9, 'reason': 'Contains spam keywords'}
    """

    def __init__(self, task: str = "spam_detection"):
        """
        Initialize the mock Claude agent.

        Args:
            task: Type of analysis to perform
                  Options: "spam_detection", "sentiment_analysis", "urgency_detection"
        """
        self.task = task
        self.call_count = 0

    def run(self, text: str) -> Any:
        """
        Process text using keyword matching.

        This mirrors ClaudeAgent.run() exactly but uses simple rules
        instead of AI.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with analysis results (format depends on task)
        """
        self.call_count += 1

        if self.task == "spam_detection":
            return self._detect_spam(text)
        elif self.task == "sentiment_analysis":
            return self._analyze_sentiment(text)
        elif self.task == "urgency_detection":
            return self._detect_urgency(text)
        else:
            raise ValueError(f"Unknown task: {self.task}")

    def _detect_spam(self, text: str) -> Dict[str, Any]:
        """Keyword-based spam detection."""
        spam_keywords = [
            'click here', 'buy now', 'limited time', 'act now',
            'free money', 'winner', 'click this', 'amazing deal',
            'get rich', 'make money fast', 'you won'
        ]

        text_lower = text.lower()
        matches = [kw for kw in spam_keywords if kw in text_lower]

        is_spam = len(matches) > 0
        confidence = min(0.9, len(matches) * 0.3) if is_spam else 0.1

        return {
            "is_spam": is_spam,
            "confidence": confidence,
            "reason": f"Contains spam keywords: {matches}" if is_spam else "No spam indicators found"
        }

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Keyword-based sentiment analysis."""
        positive_words = [
            'amazing', 'best', 'excited', 'great', 'promoted', 'love',
            'incredible', 'forward', 'happy', 'excellent', 'wonderful'
        ]
        negative_words = [
            'terrible', 'lost', 'stuck', 'worst', 'hate', 'bad',
            'awful', 'disappointing', 'frustrated', 'angry'
        ]

        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            sentiment = "POSITIVE"
            score = min(1.0, pos_count * 0.3)
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
            score = max(-1.0, -neg_count * 0.3)
        else:
            sentiment = "NEUTRAL"
            score = 0.0

        reasoning = f"Found {pos_count} positive and {neg_count} negative keywords"

        return {
            "sentiment": sentiment,
            "score": score,
            "reasoning": reasoning
        }

    def _detect_urgency(self, text: str) -> Dict[str, Any]:
        """Keyword-based urgency detection."""
        urgent_indicators = [
            '!', 'urgent', 'asap', 'immediately', 'critical',
            'breaking', 'now', 'emergency', 'important'
        ]

        text_lower = text.lower()
        urgency_score = sum(
            1 for indicator in urgent_indicators if indicator in text_lower)

        if urgency_score >= 3:
            urgency = "HIGH"
        elif urgency_score >= 1:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        metrics = {
            "urgency_score": urgency_score,
            "time_sensitive": urgency_score >= 2,
            "requires_immediate_action": urgency_score >= 3
        }

        reasoning = f"Found {urgency_score} urgency indicators"

        return {
            "urgency": urgency,
            "metrics": metrics,
            "reasoning": reasoning
        }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics (mirrors ClaudeAgent interface).

        Returns:
            Dictionary with call_count and cost (always $0 for mock)
        """
        return {
            "call_count": self.call_count,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0
        }

    def print_usage_stats(self):
        """Print usage statistics in a readable format."""
        stats = self.get_usage_stats()
        print("\n" + "=" * 60)
        print("Mock Claude Agent Usage Statistics")
        print("=" * 60)
        print(f"Task:            {self.task}")
        print(
            f"API Calls:       {stats['call_count']} (mock - no real API calls)")
        print(f"Estimated Cost:  $0.00 (mock - no charges)")
        print("=" * 60 + "\n")


# ============================================================================
# Convenience Factory Functions (mirror ClaudeAgent)
# ============================================================================

def create_spam_detector() -> MockClaudeAgent:
    """
    Create a mock spam detection agent.

    Returns:
        MockClaudeAgent configured for spam detection
    """
    return MockClaudeAgent(task="spam_detection")


def create_sentiment_analyzer() -> MockClaudeAgent:
    """
    Create a mock sentiment analysis agent.

    Returns:
        MockClaudeAgent configured for sentiment analysis
    """
    return MockClaudeAgent(task="sentiment_analysis")


def create_urgency_detector() -> MockClaudeAgent:
    """
    Create a mock urgency detection agent.

    Returns:
        MockClaudeAgent configured for urgency detection
    """
    return MockClaudeAgent(task="urgency_detection")
