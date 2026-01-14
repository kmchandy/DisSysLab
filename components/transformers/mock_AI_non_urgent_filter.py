class MockAINonUrgentFilter:
    def __init__(self):
        self.urgent_keywords = [
            'urgent', 'asap', 'immediately', 'critical',
            'breaking',  'emergency', 'important']

    def __call__(self, text):
        text_lower = text.lower()
        urgency_score = sum(
            1 for w in self.urgent_keywords if w in text_lower)
        if urgency_score < 1:
            return None
        else:
            return text
    run = __call__
