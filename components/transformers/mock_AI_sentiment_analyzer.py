class MockAISentimentAnalyzer:
    def __init__(self):
        self.positive_words = [
            'amazing', 'best', 'excited', 'great', 'promoted', 'love',
            'incredible', 'forward', 'happy', 'excellent', 'wonderful'
        ]
        self.negative_words = [
            'terrible', 'lost', 'stuck', 'worst', 'hate', 'bad',
            'awful', 'disappointing', 'frustrated', 'angry'
        ]

    def __call__(self, text):
        text_lower = text.lower()
        pos_words = [
            word for word in self.positive_words if word in text_lower]
        neg_words = [
            word for word in self.negative_words if word in text_lower]
        pos_count = sum(
            1 for word in self.positive_words if word in text_lower)
        neg_count = sum(
            1 for word in self.negative_words if word in text_lower)

        if pos_count > neg_count:
            sentiment = "POSITIVE"
            score = min(1.0, pos_count * 0.3)
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
            score = max(-1.0, -neg_count * 0.3)
        else:
            sentiment = "NEUTRAL"
            score = 0.0

        reasoning = f"Found {pos_words} positive and {neg_words} negative keywords"

        return {
            "sentiment": sentiment,
            "score": score,
            "reasoning": reasoning
        }
    run = __call__
