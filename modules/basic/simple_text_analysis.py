# modules/basic/simple_text_analysis.py

"""
Pure Python functions for text analysis.

These are ordinary functions that do not use features from 
distributed systems, message passing, threads, or processes.

They can be tested, debugged, and used independently of each other 
and independent of DSL.

You can use DSL to make a distributed network in which agents call these
functions.
"""

# Example data for different social media platforms
# Note: These are just strings, not dicts - general-purpose data
example_posts_from_X = [
    "Just got promoted at work! Best day ever! 🎉",  # HAS EMOJI
    "Breaking: New tech announced!",
    "CLICK HERE for FREE MONEY! Limited time offer!",  # SPAM
    "Just had the best lunch ever",
    "ACT NOW! Buy now and save! Winner selected!"  # SPAM
]

example_posts_from_Reddit = [
    "Had an amazing coffee this morning ☕",  # HAS EMOJI
    "Amazing discovery in science",
    "Click here to claim your free money now!",  # SPAM
    "Looking forward to the weekend",
    "Excited to start my new project tomorrow!",
    "Limited time winner! Act now or miss out!"  # SPAM
]

example_posts_from_Facebook = [
    "Traffic is terrible today, stuck for 2 hours 😤",
    "Family vacation was incredible",
    "My package got lost in delivery again...",
    "Terrible customer service today"
]


class SourceOfSocialMediaPosts:
    """
    General-purpose class that iterates through a list of posts.

    This class knows nothing about DSL, messages, or distributed systems.
    It's just a simple iterator over a list of strings.
    """

    def __init__(self, posts, name="social_media"):
        """
        Args:
            posts: List of strings (social media posts)
            name: Optional name for debugging
        """
        self.posts = posts
        self.name = name
        self.index = 0

    def run(self):
        """
        Return next post or None when exhausted.

        Returns:
            str: Next post text, or None if no more posts
        """
        if self.index >= len(self.posts):
            return None

        post = self.posts[self.index]
        self.index += 1
        return post  # Returns a string, not a dict


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


def spam_filter(text):
    """
    Classifies messages as spam or not spam.

    Args:
        text: String to check for spam

    Returns:
        Tuple of (text, is_spam) where:
        - text: original text
        - is_spam: boolean indicating if spam detected
    """
    spam_keywords = ['click here', 'buy now', 'limited time',
                     'act now', 'free money', 'winner']

    text_lower = text.lower()
    is_spam = any(keyword in text_lower for keyword in spam_keywords)

    return text, is_spam


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


def filter_non_urgent(text):
    """
    Analyzes urgency and calculates text metrics.

    This is a pure Python function - it knows nothing about distributed systems.

    Args:
        text: String to analyze

    Returns:
        Tuple of (urgency, metrics) where:
        - urgency: "HIGH", "MEDIUM", or "LOW"
        - metrics: dict with char_count, word_count, urgency_score
    """
    urgent_indicators = ['!', 'urgent', 'asap',
                         'immediately', 'critical', 'breaking']

    text_lower = text.lower()
    urgency_score = sum(
        1 for indicator in urgent_indicators if indicator in text_lower)

    if urgency_score >= 2:
        return text
    else:
        return None
# modules/basic/mock_email_alerter.py


"""
Mock Email Alerter - simulates sending email alerts.

In Module 9, this will be replaced with a real EmailAlerter that sends
actual emails via SMTP.
"""


class MockEmailAlerter:
    """
    Mock email alerter that prints alerts instead of sending real emails.

    This is a placeholder for the real EmailAlerter that students will
    use in Module 9 when they have SMTP credentials configured.
    """

    def __init__(self, recipient="admin@example.com", subject_prefix="[ALERT]"):
        """
        Args:
            recipient: Email address to send alerts to (not used in mock)
            subject_prefix: Prefix for email subject lines
        """
        self.recipient = recipient
        self.subject_prefix = subject_prefix
        self.alert_count = 0

    def run(self, msg):
        """
        Simulates sending an email alert.

        In the real version, this would use SMTP to send actual emails.
        For now, it just prints to console.

        Args:
            msg: Dictionary containing message data
        """
        self.alert_count += 1

        print()
        print("=" * 60)
        print(f"📧 MOCK EMAIL ALERT #{self.alert_count}")
        print("=" * 60)
        print(f"To: {self.recipient}")
        print(f"Subject: {self.subject_prefix} Spam Detected")
        print()
        print(f"Message: {msg.get('text', 'N/A')}")
        print("=" * 60)
        print()

    def finalize(self):
        """Cleanup - prints summary."""
        print()
        print(f"📧 MockEmailAlerter: Sent {self.alert_count} alerts")
        print()
