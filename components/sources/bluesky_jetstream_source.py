# components/sources/bluesky_jetstream_source.py

"""
BlueSky Jetstream Source - Live streaming posts from BlueSky

This is the REAL version that connects to BlueSky's Jetstream WebSocket.
Same interface as demo_bluesky_jetstream.py - easy to swap!

Compare with demo_bluesky_jetstream.py to see the demo → real pattern.
"""

import json
from datetime import datetime, timezone


class BlueSkyJetstreamSource:
    """
    Stream live posts from BlueSky via Jetstream WebSocket.

    Same interface as DemoBlueSkyJetstream - just change the import!

    Args:
        max_posts: Maximum posts to collect (default: 100, None for unlimited)
        lifetime: Maximum seconds to stream (default: 60, None for unlimited)
        filter_keywords: Optional list of keywords to filter by
        wanted_collections: Tuple of collection types (default: app.bsky.feed.post)
        min_text_length: Minimum post text length (default: 20)
        max_text_length: Maximum post text length (default: 2000)
        language: Language filter (default: "en")

    Returns:
        Dict for each post as it arrives in real-time

    Setup:
        No authentication needed! Jetstream is public.
        Just needs internet connection.

    Example:
        >>> from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        >>> source = BlueSkyJetstreamSource(max_posts=50, lifetime=30)
        >>> while True:
        ...     post = source.run()
        ...     if post is None:
        ...         break
        ...     print(f"[LIVE] @{post['author']}: {post['text'][:50]}...")
    """

    def __init__(
        self,
        max_posts=100,
        lifetime=60,
        filter_keywords=None,
        wanted_collections=("app.bsky.feed.post",),
        min_text_length=20,
        max_text_length=2000,
        language="en"
    ):
        """
        Initialize Jetstream source.

        Args:
            max_posts: Maximum posts to collect (None for unlimited)
            lifetime: Maximum seconds to stream (None for unlimited)
            filter_keywords: Optional list of keywords to filter by
            wanted_collections: Tuple of collection types
            min_text_length: Minimum post text length
            max_text_length: Maximum post text length
            language: Language filter (e.g., "en")
        """
        # Import here so demo version doesn't need the library
        try:
            import websocket
            self.websocket = websocket
        except ImportError:
            raise ImportError(
                "Jetstream requires 'websocket-client' library.\n"
                "Install it with: pip install websocket-client"
            )

        self.max_posts = max_posts
        self.lifetime = lifetime
        self.filter_keywords = [
            k.lower() for k in filter_keywords] if filter_keywords else None
        self.wanted_collections = wanted_collections
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.language = language

        self.posts_collected = 0
        self.start_time = None
        self.n = 0
        self.data = []

        # Connect and collect posts
        self._collect_posts()

        print(f"[BlueSkyJetstream] Collected {len(self.data)} posts")

    def _collect_posts(self):
        """Connect to Jetstream and collect posts."""
        print(f"[BlueSkyJetstream] Connecting to Jetstream WebSocket...")
        print(f"[BlueSkyJetstream] Max posts: {self.max_posts or 'unlimited'}")
        print(f"[BlueSkyJetstream] Lifetime: {self.lifetime or 'unlimited'}s")

        if self.filter_keywords:
            print(
                f"[BlueSkyJetstream] Filtering by keywords: {self.filter_keywords}")

        # Jetstream WebSocket URL
        jetstream_url = "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=" + \
            ",".join(self.wanted_collections)

        self.start_time = datetime.now(timezone.utc)

        try:
            ws = self.websocket.create_connection(jetstream_url)
            print(f"[BlueSkyJetstream] Connected! Streaming posts...")

            while True:
                # Check if we should stop
                if self._should_stop():
                    break

                # Receive message
                try:
                    message = ws.recv()
                    if not message:
                        break

                    # Parse JSON
                    event = json.loads(message)

                    # Process post
                    post = self._process_event(event)
                    if post:
                        self.data.append(post)
                        self.posts_collected += 1

                        if self.posts_collected % 10 == 0:
                            print(
                                f"[BlueSkyJetstream] Collected {self.posts_collected} posts...")

                except self.websocket.WebSocketTimeoutException:
                    continue
                except json.JSONDecodeError:
                    continue

            ws.close()

        except Exception as e:
            print(f"[BlueSkyJetstream] Error: {e}")
            # Continue with whatever posts we collected

    def _should_stop(self):
        """Check if we should stop collecting."""
        # Check max posts
        if self.max_posts and self.posts_collected >= self.max_posts:
            return True

        # Check lifetime
        if self.lifetime:
            elapsed = (datetime.now(timezone.utc) -
                       self.start_time).total_seconds()
            if elapsed >= self.lifetime:
                return True

        return False

    def _process_event(self, event):
        """Process Jetstream event into our standard post format."""
        try:
            # Extract commit data
            commit = event.get("commit", {})
            record = commit.get("record", {})

            # Get text
            text = record.get("text", "").strip()

            # Filter by text length
            if len(text) < self.min_text_length or len(text) > self.max_text_length:
                return None

            # Filter by language
            langs = record.get("langs", [])
            if self.language and self.language not in langs:
                return None

            # Extract hashtags
            hashtags = []
            words = text.split()
            hashtags = [word[1:].lower()
                        for word in words if word.startswith('#')]

            # Filter by keywords (if specified)
            if self.filter_keywords:
                text_lower = text.lower()
                hashtags_lower = hashtags

                found = False
                for keyword in self.filter_keywords:
                    if keyword in text_lower or keyword in hashtags_lower:
                        found = True
                        break

                if not found:
                    return None

            # Get author info
            did = event.get("did", "")

            # Build standard post dict
            return {
                "text": text,
                # Simplified author
                "author": did.split(":")[-1] if did else "unknown",
                "author_display": did.split(":")[-1] if did else "unknown",
                "timestamp": commit.get("rev", ""),
                "likes": 0,  # Not available in stream
                "reposts": 0,  # Not available in stream
                "replies": 0,  # Not available in stream
                "url": f"https://bsky.app/...",  # Simplified
                "hashtags": hashtags,
                "language": langs[0] if langs else "en"
            }

        except Exception as e:
            # Skip malformed posts
            return None

    def run(self):
        """
        Return next post from collected stream.

        Returns None when stream ends.
        """
        v = self.data[self.n] if self.n < len(self.data) else None
        self.n += 1
        return v


# Test when run directly
if __name__ == "__main__":
    import sys

    print("BlueSky Jetstream Source - Test")
    print("=" * 60)

    print("\n⚠️  This will connect to live BlueSky Jetstream")
    print("Streaming posts for 10 seconds...")
    print("-" * 60)

    try:
        # Stream for 10 seconds, max 20 posts
        source = BlueSkyJetstreamSource(
            max_posts=20,
            lifetime=10,
            # Filter to interesting posts
            filter_keywords=["python", "ai", "tech"]
        )

        print("\nPosts collected from stream:")
        print("-" * 60)

        count = 0
        finished = False

        while not finished:
            post = source.run()
            if post:
                count += 1
                print(f"\n{count}. @{post['author']}")
                print(f"   {post['text'][:80]}...")
                print(f"   Hashtags: {post['hashtags']}")
            finished = post is None

        print("\n" + "=" * 60)
        print(f"✓ Jetstream works! Collected {count} posts from live stream")

    except KeyboardInterrupt:
        print("\n\nStopped by user")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you have internet connection.")
        print("Install websocket-client: pip install websocket-client")
