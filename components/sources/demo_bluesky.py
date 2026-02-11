# components/sources/demo_bluesky.py

"""
Demo BlueSky Source - Sample social media posts for learning

This demo version uses pre-loaded sample posts so students can learn
social media monitoring without needing API credentials.

Compare with bluesky_source.py to see the demo → real pattern.
"""


class DemoBlueSkySource:
    """
    Demo BlueSky source with built-in sample posts.

    No setup needed - works immediately with realistic sample data.

    Args:
        filter_hashtag: Optional hashtag to filter by
        filter_author: Optional author to filter by
        max_posts: Maximum posts to return (default: 30)

    Returns:
        Dict for each post with full metadata

    Example:
        >>> from components.sources.demo_bluesky import DemoBlueSkySource
        >>> source = DemoBlueSkySource(max_posts=10)
        >>> while True:
        ...     post = source.run()
        ...     if post is None:
        ...         break
        ...     print(f"@{post['author']}: {post['text']}")
    """

    # Embedded sample posts - realistic BlueSky-style data
    SAMPLE_POSTS = [
        # Tech/Development posts (positive sentiment)
        {
            "text": "Just shipped our new API! Developers are going to love the webhooks feature 🚀",
            "author": "dev_sarah",
            "author_display": "Sarah Chen",
            "timestamp": "2026-02-08T14:22:00Z",
            "likes": 42,
            "reposts": 5,
            "replies": 8,
            "url": "https://bsky.app/profile/dev_sarah/post/abc123",
            "hashtags": ["api", "developers"],
            "language": "en"
        },
        {
            "text": "Python 3.13 is amazing! The performance improvements are real. Loving the new features.",
            "author": "pythonista_mike",
            "author_display": "Mike Rodriguez",
            "timestamp": "2026-02-08T10:15:00Z",
            "likes": 28,
            "reposts": 3,
            "replies": 5,
            "url": "https://bsky.app/profile/pythonista_mike/post/def456",
            "hashtags": ["python", "programming"],
            "language": "en"
        },

        # Product feedback (negative sentiment)
        {
            "text": "Really frustrated with the checkout process. Third failed payment this week. @support please help!",
            "author": "customer_anna",
            "author_display": "Anna Williams",
            "timestamp": "2026-02-08T09:30:00Z",
            "likes": 3,
            "reposts": 0,
            "replies": 2,
            "url": "https://bsky.app/profile/customer_anna/post/ghi789",
            "hashtags": [],
            "language": "en"
        },
        {
            "text": "Your mobile app keeps crashing when I try to upload photos. This is unacceptable for a paid service.",
            "author": "frustrated_user",
            "author_display": "John Davis",
            "timestamp": "2026-02-08T11:45:00Z",
            "likes": 7,
            "reposts": 1,
            "replies": 4,
            "url": "https://bsky.app/profile/frustrated_user/post/jkl012",
            "hashtags": ["buggy", "disappointed"],
            "language": "en"
        },

        # Product announcements (positive)
        {
            "text": "🎉 Excited to announce our new AI-powered search feature! Try it out and let us know what you think.",
            "author": "product_team",
            "author_display": "Product Team",
            "timestamp": "2026-02-08T13:00:00Z",
            "likes": 156,
            "reposts": 23,
            "replies": 31,
            "url": "https://bsky.app/profile/product_team/post/mno345",
            "hashtags": ["ai", "newfeature", "launch"],
            "language": "en"
        },

        # Customer inquiries (neutral)
        {
            "text": "Quick question: does your API support webhooks for real-time notifications? Can't find it in the docs.",
            "author": "developer_alex",
            "author_display": "Alex Thompson",
            "timestamp": "2026-02-08T08:20:00Z",
            "likes": 5,
            "reposts": 0,
            "replies": 3,
            "url": "https://bsky.app/profile/developer_alex/post/pqr678",
            "hashtags": ["api", "question"],
            "language": "en"
        },
        {
            "text": "Anyone know when the new pricing tiers will be available? Considering upgrading but need more info.",
            "author": "startup_founder",
            "author_display": "Emma Lee",
            "timestamp": "2026-02-08T12:10:00Z",
            "likes": 12,
            "reposts": 2,
            "replies": 6,
            "url": "https://bsky.app/profile/startup_founder/post/stu901",
            "hashtags": ["pricing", "business"],
            "language": "en"
        },

        # Positive reviews
        {
            "text": "Just have to say, your customer support team is incredible. Fixed my issue in under 10 minutes. Thank you! 🙏",
            "author": "happy_customer",
            "author_display": "Lisa Garcia",
            "timestamp": "2026-02-08T15:30:00Z",
            "likes": 89,
            "reposts": 4,
            "replies": 7,
            "url": "https://bsky.app/profile/happy_customer/post/vwx234",
            "hashtags": ["customersupport", "thankful"],
            "language": "en"
        },
        {
            "text": "Love the simplicity of this tool. Does exactly what I need without the bloat. Highly recommend!",
            "author": "minimalist_dev",
            "author_display": "Chris Park",
            "timestamp": "2026-02-08T16:00:00Z",
            "likes": 34,
            "reposts": 6,
            "replies": 9,
            "url": "https://bsky.app/profile/minimalist_dev/post/yza567",
            "hashtags": ["productivity", "tools"],
            "language": "en"
        },

        # Spam/promotional content
        {
            "text": "🔥 AMAZING OFFER! Get 90% OFF premium membership TODAY ONLY! Click here now! Limited spots!!! 💰💰💰",
            "author": "promo_bot",
            "author_display": "Special Offers",
            "timestamp": "2026-02-08T07:00:00Z",
            "likes": 0,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/promo_bot/post/spam1",
            "hashtags": ["discount", "sale", "offer"],
            "language": "en"
        },
        {
            "text": "YOU WON'T BELIEVE THIS SECRET! Make $10000 in ONE WEEK!!! Click the link in bio!!! 🤑🤑🤑",
            "author": "scam_account",
            "author_display": "Make Money Fast",
            "timestamp": "2026-02-08T06:30:00Z",
            "likes": 1,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/scam_account/post/spam2",
            "hashtags": ["money", "opportunity"],
            "language": "en"
        },

        # More tech discussions
        {
            "text": "Working on a distributed systems project. Any recommendations for good testing frameworks?",
            "author": "student_coder",
            "author_display": "Jamie Wilson",
            "timestamp": "2026-02-08T14:45:00Z",
            "likes": 18,
            "reposts": 2,
            "replies": 15,
            "url": "https://bsky.app/profile/student_coder/post/abc890",
            "hashtags": ["coding", "help"],
            "language": "en"
        },
        {
            "text": "Just discovered this framework for building distributed apps. The DSL approach is genius!",
            "author": "tech_enthusiast",
            "author_display": "Sam Martinez",
            "timestamp": "2026-02-08T17:20:00Z",
            "likes": 67,
            "reposts": 12,
            "replies": 18,
            "url": "https://bsky.app/profile/tech_enthusiast/post/def123",
            "hashtags": ["framework", "distributed"],
            "language": "en"
        },

        # More customer feedback
        {
            "text": "The new update broke my workflow. The old interface was much better. Please add a classic mode option.",
            "author": "longtime_user",
            "author_display": "Taylor Brown",
            "timestamp": "2026-02-08T11:00:00Z",
            "likes": 23,
            "reposts": 5,
            "replies": 12,
            "url": "https://bsky.app/profile/longtime_user/post/ghi456",
            "hashtags": ["feedback", "ux"],
            "language": "en"
        },
        {
            "text": "Feature request: dark mode! My eyes would be so grateful. 😎",
            "author": "night_owl",
            "author_display": "Morgan Lee",
            "timestamp": "2026-02-08T23:30:00Z",
            "likes": 45,
            "reposts": 8,
            "replies": 21,
            "url": "https://bsky.app/profile/night_owl/post/jkl789",
            "hashtags": ["feature", "darkmode"],
            "language": "en"
        },

        # Mixed sentiment
        {
            "text": "The core product is solid, but the documentation needs work. Hard to find what I need sometimes.",
            "author": "dev_reviewer",
            "author_display": "Casey Johnson",
            "timestamp": "2026-02-08T10:30:00Z",
            "likes": 31,
            "reposts": 4,
            "replies": 9,
            "url": "https://bsky.app/profile/dev_reviewer/post/mno012",
            "hashtags": ["docs", "feedback"],
            "language": "en"
        },

        # More positive
        {
            "text": "Been using this for 6 months now. Absolutely game-changing for our team's productivity!",
            "author": "team_lead",
            "author_display": "Jordan Smith",
            "timestamp": "2026-02-08T13:45:00Z",
            "likes": 52,
            "reposts": 7,
            "replies": 14,
            "url": "https://bsky.app/profile/team_lead/post/pqr345",
            "hashtags": ["productivity", "teamwork"],
            "language": "en"
        },

        # Casual/neutral
        {
            "text": "Anyone else at the tech conference this week? Would love to connect!",
            "author": "conference_goer",
            "author_display": "Avery Kim",
            "timestamp": "2026-02-08T09:00:00Z",
            "likes": 14,
            "reposts": 3,
            "replies": 8,
            "url": "https://bsky.app/profile/conference_goer/post/stu678",
            "hashtags": ["conference", "networking"],
            "language": "en"
        },
        {
            "text": "Just finished reading the latest blog post. Interesting insights on scaling distributed systems.",
            "author": "tech_reader",
            "author_display": "Riley Chen",
            "timestamp": "2026-02-08T16:30:00Z",
            "likes": 29,
            "reposts": 5,
            "replies": 6,
            "url": "https://bsky.app/profile/tech_reader/post/vwx901",
            "hashtags": ["tech", "blog"],
            "language": "en"
        },

        # More spam
        {
            "text": "FREE CRYPTO GIVEAWAY!!! 🚀🚀🚀 First 100 people get 10 BTC!!! Follow and RT!!! DON'T MISS OUT!!!",
            "author": "crypto_scam",
            "author_display": "Crypto Giveaway",
            "timestamp": "2026-02-08T05:00:00Z",
            "likes": 2,
            "reposts": 0,
            "replies": 0,
            "url": "https://bsky.app/profile/crypto_scam/post/spam3",
            "hashtags": ["crypto", "giveaway", "bitcoin"],
            "language": "en"
        },

        # Final batch - various
        {
            "text": "The integration with Slack is perfect. Exactly what we needed for our workflow.",
            "author": "workflow_optimizer",
            "author_display": "Dakota Martinez",
            "timestamp": "2026-02-08T14:00:00Z",
            "likes": 38,
            "reposts": 6,
            "replies": 11,
            "url": "https://bsky.app/profile/workflow_optimizer/post/yza234",
            "hashtags": ["integration", "slack"],
            "language": "en"
        },
        {
            "text": "How do I export my data? Can't find the option anywhere in settings.",
            "author": "data_seeker",
            "author_display": "Quinn Taylor",
            "timestamp": "2026-02-08T12:45:00Z",
            "likes": 6,
            "reposts": 0,
            "replies": 4,
            "url": "https://bsky.app/profile/data_seeker/post/abc567",
            "hashtags": ["help", "export"],
            "language": "en"
        },
        {
            "text": "Shoutout to the team for the quick bug fix! Appreciate the fast response time. 👍",
            "author": "grateful_dev",
            "author_display": "Blake Anderson",
            "timestamp": "2026-02-08T15:00:00Z",
            "likes": 71,
            "reposts": 3,
            "replies": 5,
            "url": "https://bsky.app/profile/grateful_dev/post/def890",
            "hashtags": ["bugfix", "thanks"],
            "language": "en"
        },
        {
            "text": "Is there a student discount available? Asking for my university project.",
            "author": "student_dev",
            "author_display": "Peyton Lee",
            "timestamp": "2026-02-08T11:15:00Z",
            "likes": 9,
            "reposts": 1,
            "replies": 3,
            "url": "https://bsky.app/profile/student_dev/post/ghi123",
            "hashtags": ["student", "pricing"],
            "language": "en"
        },
        {
            "text": "The mobile app needs better offline support. Loses all data when connection drops.",
            "author": "mobile_user",
            "author_display": "River Johnson",
            "timestamp": "2026-02-08T10:00:00Z",
            "likes": 19,
            "reposts": 4,
            "replies": 7,
            "url": "https://bsky.app/profile/mobile_user/post/jkl456",
            "hashtags": ["mobile", "feature"],
            "language": "en"
        },
        {
            "text": "Just hit 1000 users for our app built with this framework! Couldn't have done it without these tools.",
            "author": "indie_maker",
            "author_display": "Sage Kim",
            "timestamp": "2026-02-08T18:00:00Z",
            "likes": 124,
            "reposts": 18,
            "replies": 26,
            "url": "https://bsky.app/profile/indie_maker/post/mno789",
            "hashtags": ["milestone", "indiehacker"],
            "language": "en"
        },
        {
            "text": "Documentation is top-notch. Found everything I needed in under 5 minutes. Great job!",
            "author": "doc_fan",
            "author_display": "Cameron White",
            "timestamp": "2026-02-08T13:15:00Z",
            "likes": 43,
            "reposts": 5,
            "replies": 8,
            "url": "https://bsky.app/profile/doc_fan/post/pqr012",
            "hashtags": ["docs", "praise"],
            "language": "en"
        },
        {
            "text": "When will the enterprise features be ready? Our team is ready to upgrade.",
            "author": "enterprise_buyer",
            "author_display": "Morgan Davis",
            "timestamp": "2026-02-08T14:30:00Z",
            "likes": 22,
            "reposts": 2,
            "replies": 9,
            "url": "https://bsky.app/profile/enterprise_buyer/post/stu345",
            "hashtags": ["enterprise", "upgrade"],
            "language": "en"
        },
        {
            "text": "Performance is incredible after the latest update. Everything feels so much snappier!",
            "author": "speed_demon",
            "author_display": "Skylar Martinez",
            "timestamp": "2026-02-08T16:45:00Z",
            "likes": 58,
            "reposts": 9,
            "replies": 12,
            "url": "https://bsky.app/profile/speed_demon/post/vwx678",
            "hashtags": ["performance", "update"],
            "language": "en"
        },
        {
            "text": "Having trouble connecting to the database. Error message isn't very helpful. Any ideas?",
            "author": "troubleshooter",
            "author_display": "Reese Wilson",
            "timestamp": "2026-02-08T09:45:00Z",
            "likes": 11,
            "reposts": 1,
            "replies": 13,
            "url": "https://bsky.app/profile/troubleshooter/post/yza901",
            "hashtags": ["help", "database"],
            "language": "en"
        }
    ]

    def __init__(self, filter_hashtag=None, filter_author=None, max_posts=30):
        """
        Initialize demo BlueSky source.

        Args:
            filter_hashtag: Optional hashtag to filter by (e.g., "python")
            filter_author: Optional author to filter by (e.g., "dev_sarah")
            max_posts: Maximum posts to return (default: 30)
        """
        self.filter_hashtag = filter_hashtag.lower() if filter_hashtag else None
        self.filter_author = filter_author.lower() if filter_author else None
        self.max_posts = max_posts
        self.n = 0

        # Filter posts based on criteria
        self.data = self._filter_posts()

        print(f"[DemoBlueSkySource] Loaded {len(self.data)} posts")
        if self.filter_hashtag:
            print(
                f"[DemoBlueSkySource] Filtered by hashtag: #{self.filter_hashtag}")
        if self.filter_author:
            print(
                f"[DemoBlueSkySource] Filtered by author: @{self.filter_author}")

    def _filter_posts(self):
        """Filter posts based on criteria and limit to max_posts."""
        filtered = []

        for post in self.SAMPLE_POSTS:
            # Filter by hashtag
            if self.filter_hashtag:
                if self.filter_hashtag not in [tag.lower() for tag in post["hashtags"]]:
                    continue

            # Filter by author
            if self.filter_author:
                if post["author"].lower() != self.filter_author:
                    continue

            filtered.append(post)

            # Stop if we've reached max_posts
            if len(filtered) >= self.max_posts:
                break

        return filtered

    def run(self):
        """
        Return next post.

        Returns None when complete (signals end of stream).
        """
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# Test when run directly
if __name__ == "__main__":
    print("Demo BlueSky Source - Test")
    print("=" * 60)

    # Test 1: All posts
    print("\nTest 1: All Posts")
    print("-" * 60)
    source = DemoBlueSkySource(max_posts=5)
    count = 0
    finished = False
    while not finished:
        post = source.run()
        if post:
            print(f"  @{post['author']}: {post['text'][:50]}...")
            print(f"    Likes: {post['likes']}, Hashtags: {post['hashtags']}")
        count += 1
        finished = post is None
    print(f"  Total: {count - 1} posts")

    # Test 2: Filter by hashtag
    print("\nTest 2: Filter by Hashtag (#python)")
    print("-" * 60)
    source = DemoBlueSkySource(filter_hashtag="python", max_posts=10)
    finished = False
    while not finished:
        post = source.run()
        if post:
            print(f"  @{post['author']}: {post['text'][:50]}...")
        finished = post is None

    # Test 3: Filter by author
    print("\nTest 3: Filter by Author (@dev_sarah)")
    print("-" * 60)
    source = DemoBlueSkySource(filter_author="dev_sarah", max_posts=10)
    finished = False
    while not finished:
        post = source.run()
        if post:
            print(f"  @{post['author']}: {post['text'][:50]}...")
        finished = post is None

    print("\n" + "=" * 60)
    print("✓ Demo BlueSky Source works!")
