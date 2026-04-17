# components/sources/demo_bluesky_jetstream.py

"""
Demo BlueSky Jetstream - Simulate live streaming posts

This demo version simulates a live stream by yielding sample posts
with time delays, so students can learn streaming patterns offline.

Compare with bluesky_jetstream_source.py to see the demo → real pattern.
"""

import time


class DemoBlueSkyJetstream:
    """
    Demo Jetstream source - simulates live streaming posts.

    Yields posts with delays to simulate real-time streaming.
    No setup needed - works offline!

    Args:
        max_posts: Maximum posts to stream (default: 20)
        delay_seconds: Delay between posts in seconds (default: 0.5)
        filter_keywords: Optional list of keywords to filter by

    Returns:
        Dict for each post as it "arrives" (same structure as real Jetstream)

    Example:
        >>> from components.sources.demo_bluesky_jetstream import DemoBlueSkyJetstream
        >>> source = DemoBlueSkyJetstream(max_posts=10, delay_seconds=1)
        >>> while True:
        ...     post = source.run()
        ...     if post is None:
        ...         break
        ...     print(f"[LIVE] @{post['author']}: {post['text'][:50]}...")
    """

    # Embedded sample posts - simulates live stream
    SAMPLE_STREAM = [
        {
            "text": "Just deployed the new API! Developers are going to love this 🚀",
            "author": "dev_sarah",
            "author_display": "Sarah Chen",
            "timestamp": "2026-02-10T14:22:00Z",
            "likes": 0,  # Stream starts with 0, grows over time
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/dev_sarah/post/live1",
            "hashtags": ["api", "release"],
            "language": "en"
        },
        {
            "text": "Excited to announce our new AI search feature! Try it out 🎉",
            "author": "product_team",
            "author_display": "Product Team",
            "timestamp": "2026-02-10T14:23:15Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/product_team/post/live2",
            "hashtags": ["ai", "launch"],
            "language": "en"
        },
        {
            "text": "The checkout is broken AGAIN! This is frustrating. @support help!",
            "author": "angry_customer",
            "author_display": "Frustrated User",
            "timestamp": "2026-02-10T14:24:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/angry_customer/post/live3",
            "hashtags": ["support", "bug"],
            "language": "en"
        },
        {
            "text": "Your customer support is amazing! Fixed my issue in 5 minutes. Thank you! 🙏",
            "author": "happy_user",
            "author_display": "Lisa Garcia",
            "timestamp": "2026-02-10T14:25:30Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/happy_user/post/live4",
            "hashtags": ["support", "thanks"],
            "language": "en"
        },
        {
            "text": "🔥 AMAZING DEAL!!! 90% OFF TODAY ONLY!!! Click now!!! 💰💰💰",
            "author": "spam_bot",
            "author_display": "Special Offers",
            "timestamp": "2026-02-10T14:26:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/spam_bot/post/live5",
            "hashtags": ["sale", "deal"],
            "language": "en"
        },
        {
            "text": "Quick question: does your API support webhooks? Can't find it in docs.",
            "author": "dev_alex",
            "author_display": "Alex Thompson",
            "timestamp": "2026-02-10T14:27:15Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/dev_alex/post/live6",
            "hashtags": ["api", "question"],
            "language": "en"
        },
        {
            "text": "Love this framework! Building a distributed app has never been easier.",
            "author": "builder_sam",
            "author_display": "Sam Martinez",
            "timestamp": "2026-02-10T14:28:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/builder_sam/post/live7",
            "hashtags": ["framework", "coding"],
            "language": "en"
        },
        {
            "text": "The mobile app keeps crashing when uploading photos. Please fix!",
            "author": "mobile_user",
            "author_display": "Jordan Kim",
            "timestamp": "2026-02-10T14:29:30Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/mobile_user/post/live8",
            "hashtags": ["bug", "mobile"],
            "language": "en"
        },
        {
            "text": "Working on a cool distributed systems project for my CS class!",
            "author": "student_coder",
            "author_display": "Jamie Wilson",
            "timestamp": "2026-02-10T14:30:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/student_coder/post/live9",
            "hashtags": ["coding", "school"],
            "language": "en"
        },
        {
            "text": "When will the new pricing tiers be available? Ready to upgrade!",
            "author": "startup_founder",
            "author_display": "Emma Lee",
            "timestamp": "2026-02-10T14:31:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/startup_founder/post/live10",
            "hashtags": ["pricing", "business"],
            "language": "en"
        },
        {
            "text": "💎 FREE CRYPTO GIVEAWAY!!! First 100 people!!! DON'T MISS OUT!!! 🚀🚀🚀",
            "author": "crypto_scam",
            "author_display": "Crypto Giveaway",
            "timestamp": "2026-02-10T14:32:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/crypto_scam/post/live11",
            "hashtags": ["crypto", "scam"],
            "language": "en"
        },
        {
            "text": "The new update is perfect! Performance is so much better now.",
            "author": "power_user",
            "author_display": "Chris Park",
            "timestamp": "2026-02-10T14:33:15Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/power_user/post/live12",
            "hashtags": ["update", "performance"],
            "language": "en"
        },
        {
            "text": "Feature request: please add dark mode! My eyes would be grateful 😎",
            "author": "night_coder",
            "author_display": "Taylor Brown",
            "timestamp": "2026-02-10T14:34:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/night_coder/post/live13",
            "hashtags": ["feature", "darkmode"],
            "language": "en"
        },
        {
            "text": "Just hit 1000 users for my app! Couldn't have done it without this framework.",
            "author": "indie_maker",
            "author_display": "Morgan Davis",
            "timestamp": "2026-02-10T14:35:30Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/indie_maker/post/live14",
            "hashtags": ["milestone", "success"],
            "language": "en"
        },
        {
            "text": "Documentation is excellent! Found everything I needed quickly.",
            "author": "doc_reader",
            "author_display": "Casey Johnson",
            "timestamp": "2026-02-10T14:36:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/doc_reader/post/live15",
            "hashtags": ["docs", "praise"],
            "language": "en"
        },
        {
            "text": "Having database connection issues. Error messages aren't helpful.",
            "author": "troubleshooter",
            "author_display": "Reese Wilson",
            "timestamp": "2026-02-10T14:37:15Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/troubleshooter/post/live16",
            "hashtags": ["help", "database"],
            "language": "en"
        },
        {
            "text": "The integration with Slack works perfectly! Exactly what we needed.",
            "author": "team_lead",
            "author_display": "Dakota Martinez",
            "timestamp": "2026-02-10T14:38:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/team_lead/post/live17",
            "hashtags": ["integration", "slack"],
            "language": "en"
        },
        {
            "text": "Anyone at the tech conference this week? Let's connect!",
            "author": "networker",
            "author_display": "Avery Kim",
            "timestamp": "2026-02-10T14:39:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/networker/post/live18",
            "hashtags": ["conference", "networking"],
            "language": "en"
        },
        {
            "text": "Python 3.13 performance is incredible! Loving the improvements.",
            "author": "pythonista",
            "author_display": "Blake Anderson",
            "timestamp": "2026-02-10T14:40:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/pythonista/post/live19",
            "hashtags": ["python", "programming"],
            "language": "en"
        },
        {
            "text": "Is there a student discount? Asking for my university project.",
            "author": "student_dev",
            "author_display": "Quinn Taylor",
            "timestamp": "2026-02-10T14:41:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/student_dev/post/live20",
            "hashtags": ["student", "pricing"],
            "language": "en"
        }
    ]

    def __init__(self, max_posts=20, delay_seconds=0.5, filter_keywords=None):
        """
        Initialize demo Jetstream source.

        Args:
            max_posts: Maximum posts to stream (default: 20)
            delay_seconds: Delay between posts in seconds (default: 0.5)
            filter_keywords: Optional list of keywords to filter by
        """
        self.max_posts = max_posts
        self.delay_seconds = delay_seconds
        self.filter_keywords = [
            k.lower() for k in filter_keywords] if filter_keywords else None
        self.n = 0

        # Filter posts if keywords provided
        if self.filter_keywords:
            self.data = self._filter_posts()
            print(
                f"[DemoBlueSkyJetstream] Streaming up to {len(self.data)} posts (filtered by keywords)")
        else:
            self.data = self.SAMPLE_STREAM[:max_posts]
            print(
                f"[DemoBlueSkyJetstream] Streaming up to {len(self.data)} posts")

        print(
            f"[DemoBlueSkyJetstream] Simulating live stream with {delay_seconds}s delays")

    def _filter_posts(self):
        """Filter posts by keywords in text or hashtags."""
        filtered = []

        for post in self.SAMPLE_STREAM:
            # Check if any keyword appears in text or hashtags
            text_lower = post["text"].lower()
            hashtags_lower = [tag.lower() for tag in post["hashtags"]]

            for keyword in self.filter_keywords:
                if keyword in text_lower or keyword in hashtags_lower:
                    filtered.append(post)
                    break

            if len(filtered) >= self.max_posts:
                break

        return filtered

    def run(self):
        """
        Return next post from stream (with delay to simulate real-time).

        Returns None when stream ends.
        """
        if self.n >= len(self.data):
            return None

        # Simulate network delay
        if self.n > 0:  # Don't delay first post
            time.sleep(self.delay_seconds)

        post = self.data[self.n]
        self.n += 1

        print(
            f"[DemoBlueSkyJetstream] Post {self.n}/{len(self.data)} received")

        return post


# Test when run directly
if __name__ == "__main__":
    print("Demo BlueSky Jetstream - Test")
    print("=" * 60)

    # Test 1: Stream all posts
    print("\nTest 1: Streaming 5 Posts")
    print("-" * 60)
    source = DemoBlueSkyJetstream(max_posts=5, delay_seconds=0.2)

    count = 0
    finished = False
    start_time = time.time()

    while not finished:
        post = source.run()
        if post:
            elapsed = time.time() - start_time
            print(f"  [{elapsed:.1f}s] @{post['author']}: {post['text'][:50]}...")
            count += 1
        finished = post is None

    print(f"\n  Total streamed: {count} posts")

    # Test 2: Filter by keywords
    print("\n\nTest 2: Stream Posts Filtered by Keywords")
    print("-" * 60)
    source = DemoBlueSkyJetstream(
        max_posts=10,
        delay_seconds=0.1,
        filter_keywords=["api", "support"]
    )

    count = 0
    finished = False

    while not finished:
        post = source.run()
        if post:
            print(f"  @{post['author']}: {post['text'][:50]}...")
            print(f"    Hashtags: {post['hashtags']}")
            count += 1
        finished = post is None

    print(f"\n  Total streamed: {count} posts")

    print("\n" + "=" * 60)
    print("✓ Demo BlueSky Jetstream works!")
    print("  Notice the delays - this simulates a live stream!")
