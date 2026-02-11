# components/sources/bluesky_source.py

"""
BlueSky Source - Read posts from BlueSky social network

This is the REAL version that connects to BlueSky API.
Same interface as demo_bluesky.py - easy to swap!

Compare with demo_bluesky.py to see the demo → real pattern.
"""


class BlueSkySource:
    """
    Read posts from BlueSky social network via API.

    Same interface as DemoBlueSkySource - just change the import!

    Args:
        handle: Your BlueSky handle (e.g., "user.bsky.social")
        app_password: App password from BlueSky settings
        search_hashtag: Optional hashtag to search for
        search_author: Optional author handle to search for
        max_posts: Maximum posts to fetch (default: 50)

    Returns:
        Dict for each post (same structure as demo version)

    Setup:
        1. Create BlueSky account (free)
        2. Go to Settings → App Passwords
        3. Generate new app password
        4. Use that password (not your main password!)

    See API_SETUP.md for detailed instructions.

    Example:
        >>> from components.sources.bluesky_source import BlueSkySource
        >>> source = BlueSkySource(
        ...     handle="user.bsky.social",
        ...     app_password="xxxx-xxxx-xxxx-xxxx"
        ... )
        >>> while True:
        ...     post = source.run()
        ...     if post is None:
        ...         break
        ...     print(f"@{post['author']}: {post['text']}")
    """

    def __init__(
        self,
        handle,
        app_password,
        search_hashtag=None,
        search_author=None,
        max_posts=50
    ):
        """
        Initialize BlueSky source.

        Args:
            handle: Your BlueSky handle (e.g., "user.bsky.social")
            app_password: App password from BlueSky settings
            search_hashtag: Optional hashtag to search (without #)
            search_author: Optional author handle to search
            max_posts: Maximum posts to fetch (default: 50)
        """
        # Import here so demo version doesn't need the library
        try:
            from atproto import Client
        except ImportError:
            raise ImportError(
                "BlueSky API requires 'atproto' library.\n"
                "Install it with: pip install atproto"
            )

        self.handle = handle
        self.app_password = app_password
        self.search_hashtag = search_hashtag
        self.search_author = search_author
        self.max_posts = max_posts
        self.n = 0
        self.data = []

        # Authenticate
        self.client = Client()
        try:
            self.client.login(handle, app_password)
            print(f"[BlueSkySource] Authenticated as {handle}")
        except Exception as e:
            raise ValueError(
                f"BlueSky authentication failed: {e}\n"
                f"Check:\n"
                f"  1. Handle is correct (user.bsky.social)\n"
                f"  2. Using APP PASSWORD (not main password)\n"
                f"  3. App password is active\n"
                f"See API_SETUP.md for setup instructions"
            )

        # Fetch posts
        self._fetch_posts()

        print(f"[BlueSkySource] Fetched {len(self.data)} posts")

    def _fetch_posts(self):
        """Fetch posts from BlueSky API."""
        try:
            if self.search_hashtag:
                # Search by hashtag
                self._fetch_by_hashtag()
            elif self.search_author:
                # Search by author
                self._fetch_by_author()
            else:
                # Get timeline
                self._fetch_timeline()
        except Exception as e:
            print(f"[BlueSkySource] Error fetching posts: {e}")
            # Continue with empty data rather than crash

    def _fetch_timeline(self):
        """Fetch posts from user's timeline."""
        print("[BlueSkySource] Fetching posts from timeline...")

        response = self.client.get_timeline(limit=min(self.max_posts, 100))

        for item in response.feed:
            if len(self.data) >= self.max_posts:
                break

            post = item.post
            self.data.append(self._parse_post(post))

    def _fetch_by_hashtag(self):
        """Fetch posts by hashtag search."""
        print(f"[BlueSkySource] Searching for #{self.search_hashtag}...")

        # BlueSky search query
        query = f"#{self.search_hashtag}"

        response = self.client.app.bsky.feed.search_posts(
            params={'q': query, 'limit': min(self.max_posts, 100)}
        )

        for post in response.posts:
            if len(self.data) >= self.max_posts:
                break

            self.data.append(self._parse_post(post))

    def _fetch_by_author(self):
        """Fetch posts by specific author."""
        print(f"[BlueSkySource] Fetching posts from @{self.search_author}...")

        response = self.client.get_author_feed(
            actor=self.search_author,
            limit=min(self.max_posts, 100)
        )

        for item in response.feed:
            if len(self.data) >= self.max_posts:
                break

            post = item.post
            self.data.append(self._parse_post(post))

    def _parse_post(self, post):
        """Parse BlueSky post into our standard format."""
        record = post.record

        # Extract hashtags from text
        hashtags = []
        if hasattr(record, 'text'):
            words = record.text.split()
            hashtags = [word[1:].lower()
                        for word in words if word.startswith('#')]

        # Build standard post dict
        return {
            "text": record.text if hasattr(record, 'text') else "",
            "author": post.author.handle,
            "author_display": post.author.display_name or post.author.handle,
            "timestamp": record.created_at if hasattr(record, 'created_at') else "",
            "likes": post.like_count or 0,
            "reposts": post.repost_count or 0,
            "replies": post.reply_count or 0,
            "url": f"https://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}",
            "hashtags": hashtags,
            "language": record.langs[0] if hasattr(record, 'langs') and record.langs else "en"
        }

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
    import os
    import sys

    print("BlueSky Source - Test")
    print("=" * 60)

    # Check for credentials
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")

    if not handle or not password:
        print("\n⚠️  BlueSky credentials not found in environment")
        print("\nTo test this, set environment variables:")
        print("  export BLUESKY_HANDLE='your.handle.bsky.social'")
        print("  export BLUESKY_PASSWORD='xxxx-xxxx-xxxx-xxxx'")
        print("\nOr edit this file and add credentials here for testing.")
        print("\nSee API_SETUP.md for setup instructions.")
        sys.exit(0)

    # Test: Fetch timeline
    print("\nTest: Fetching timeline")
    print("-" * 60)

    try:
        source = BlueSkySource(
            handle=handle,
            app_password=password,
            max_posts=5
        )

        count = 0
        finished = False
        while not finished:
            post = source.run()
            if post:
                print(
                    f"\n{count + 1}. @{post['author']}: {post['text'][:60]}...")
                print(f"   Likes: {post['likes']}, Reposts: {post['reposts']}")
                print(f"   Hashtags: {post['hashtags']}")
                count += 1
            finished = post is None

        print("\n" + "=" * 60)
        print(f"✓ BlueSky Source works! Fetched {count} posts")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nCheck API_SETUP.md for troubleshooting.")
