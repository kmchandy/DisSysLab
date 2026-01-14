class MockAISpamFilter:
    def __init__(self):
        self.spam_keywords = [
            'click here', 'buy now', 'limited time', 'act now',
            'free money', 'winner', 'click this', 'amazing deal',
            'get rich', 'make money fast', 'you won'
            "subscribe", "limited time offer"]

    def __call__(self, text):
        text_lower = text.lower()
        num_spam_word_matches = sum(
            1 for w in self.spam_keywords if w in text_lower)
        if num_spam_word_matches > 0:
            return None
        else:
            return text
    run = __call__
