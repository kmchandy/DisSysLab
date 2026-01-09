# modules/ch01_networks/simple_text_analysis.py

"""
Pure Python functions for text analysis.

These are ordinary Python functions that do not use features from 
distributed systems, message passing, threads, or processes.

They can be tested, debugged, and used independently of each other 
and independent of dsl.

You can use dsl to make a distributed network in which agents call these
functions.
"""

# Example data for different social media platforms
example_posts_from_X = [
    {"text": "Just got promoted at work! Best day ever! 🎉", "platform": "X"},
    {"text": "Breaking: New tech announced!", "platform": "X"},
    {"text": "Just had the best lunch ever", "platform": "X"}
]

example_posts_from_Reddit = [
    {"text": "Had an amazing coffee this morning ☕", "platform": "Reddit"},
    {"text": "Amazing discovery in science", "platform": "Reddit"},
    {"text": "Looking forward to the weekend", "platform": "Reddit"},
    {"text": "Excited to start my new project tomorrow!", "platform": "Reddit"}
]

example_posts_from_Facebook = [
    {"text": "Traffic is terrible today, stuck for 2 hours 😤", "platform": "Facebook"},
    {"text": "Family vacation was incredible", "platform": "Facebook"},
    {"text": "My package got lost in delivery again...", "platform": "Facebook"},
    {"text": "Terrible customer service today", "platform": "Facebook"}
]


class SourceOfSocialMediaPosts:
    """Source that generates social media posts"""

    def __init__(
        self,
        posts: list = None,
        name: str = "from_social_media"
    ):
        self.posts = posts or []
        self.name = name

    def __call__(self):
        for post in self.posts:
            yield post

    run = __call__


def clean_text(text):
    """
    Removes emojis and cleans whitespace.

    This is a pure Python function - it knows nothing about distributed systems.

    Args:
        text: String to clean

    Returns:
        Cleaned string
    """
    import re
    cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned


def analyze_sentiment(text):
    """
    Analyzes sentiment using keyword matching.

    This is a pure Python function - it knows nothing about distributed systems.

    Args:
        text: String to analyze

    Returns:
        Tuple of (sentiment, score) where:
        - sentiment: "POSITIVE", "NEGATIVE", or "NEUTRAL"
        - score: integer score (positive_count - negative_count)
    """
    positive_words = ['amazing', 'best', 'excited', 'great', 'promoted', 'love',
                      'incredible', 'forward']
    negative_words = ['terrible', 'lost', 'stuck', 'worst', 'hate', 'bad']

    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    if pos_count > neg_count:
        sentiment = "POSITIVE"
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    score = pos_count - neg_count
    return sentiment, score


def analyze_urgency(text):
    """
    Analyzes urgency and calculates text metrics.
    """
    urgent_indicators = ['!', 'urgent', 'asap',
                         'immediately', 'critical', 'breaking']

    text_lower = text.lower()
    urgency_score = sum(
        1 for indicator in urgent_indicators if indicator in text_lower)

    if urgency_score >= 2:
        urgency = "HIGH"
    elif urgency_score == 1:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    metrics = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "urgency_score": urgency_score
    }

    return urgency, metrics
