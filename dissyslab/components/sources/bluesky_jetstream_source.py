# dissyslab/components/sources/bluesky_jetstream_source.py

"""
BlueSky Jetstream Source - Live streaming posts from BlueSky

This is the REAL version that connects to BlueSky's Jetstream WebSocket.
Posts are yielded one by one as they arrive — true real-time streaming.

Unlike the batch version, this source never pre-collects posts.
Each post flows into the DisSysLab network the moment it arrives
from the WebSocket connection.

No authentication needed — Jetstream is public.
"""

import json
from datetime import datetime, timezone


class BlueSkyJetstreamSource:
    """
    Stream live posts from BlueSky via Jetstream WebSocket.

    This is a true streaming source — posts are yielded one by one
    as they arrive from the WebSocket, not collected first.

    DisSysLab's Source block handles generators automatically, so
    each post flows into the network the moment it arrives.

    Args:
        max_posts:    Stop after this many posts (None = run forever)
        lifetime:     Stop after this many seconds (None = run forever)
        filter_keywords: Only yield posts containing these keywords
        wanted_collections: BlueSky collection types to subscribe to
        min_text_length: Skip posts shorter than this
        max_text_length: Skip posts longer than this
        language:     Only yield posts in this language (e.g. "en")

    Example:
        >>> from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
        >>> from dissyslab.blocks import Source
        >>>
        >>> jetstream = BlueSkyJetstreamSource(
        ...     max_posts=50,
        ...     filter_keywords=["AI", "python"]
        ... )
        >>> source = Source(fn=jetstream.run, name="bluesky")
    """

    def __init__(
        self,
        max_posts=100,
        lifetime=None,
        filter_keywords=None,
        wanted_collections=("app.bsky.feed.post",),
        min_text_length=20,
        max_text_length=2000,
        language="en"
    ):
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
        self.filter_keywords = (
            [k.lower() for k in filter_keywords] if filter_keywords else None
        )
        self.wanted_collections = wanted_collections
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.language = language

        # Runtime state — reset each time run() is called
        self.posts_yielded = 0
        self.start_time = None

        # Build WebSocket URL once
        self._jetstream_url = (
            "wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections="
            + ",".join(self.wanted_collections)
        )

    def _should_stop(self):
        """Check termination conditions."""
        if self.max_posts and self.posts_yielded >= self.max_posts:
            return True
        if self.lifetime and self.start_time:
            elapsed = (datetime.now(timezone.utc) -
                       self.start_time).total_seconds()
            if elapsed >= self.lifetime:
                return True
        return False

    def _process_event(self, event):
        """
        Convert a raw Jetstream event into a standard post dict.
        Returns None if the event should be skipped.
        """
        try:
            commit = event.get("commit", {})
            record = commit.get("record", {})

            text = record.get("text", "").strip()

            # Length filter
            if len(text) < self.min_text_length or len(text) > self.max_text_length:
                return None

            # Language filter
            langs = record.get("langs", [])
            if self.language and self.language not in langs:
                return None

            # Keyword filter
            if self.filter_keywords:
                text_lower = text.lower()
                if not any(kw in text_lower for kw in self.filter_keywords):
                    return None

            # Extract hashtags
            hashtags = [
                word[1:].lower()
                for word in text.split()
                if word.startswith('#')
            ]

            # Author
            did = event.get("did", "")
            author = did.split(":")[-1] if did else "unknown"

            # Wall clock timestamp — shows exactly when post arrived
            now = datetime.now().strftime("%d %b %Y  %H:%M:%S")

            return {
                "text":           text,
                "author":         author,
                "author_display": author,
                "timestamp":      now,
                "source":         "bluesky",
                "hashtags":       hashtags,
                "language":       langs[0] if langs else "en",
                "url":            f"https://bsky.app/profile/{author}",
            }

        except Exception:
            return None

    def run(self):
        """
        Generator that yields posts one by one as they arrive.

        Each post is yielded the moment it comes off the WebSocket —
        no pre-collection, no batching.

        DisSysLab's Source block wraps this generator automatically.
        """
        print(f"[BlueSkyJetstream] Connecting to Jetstream WebSocket...")
        if self.filter_keywords:
            print(f"[BlueSkyJetstream] Filtering by: {self.filter_keywords}")
        if self.max_posts:
            print(f"[BlueSkyJetstream] Max posts: {self.max_posts}")
        if self.lifetime:
            print(f"[BlueSkyJetstream] Lifetime: {self.lifetime}s")

        self.posts_yielded = 0
        self.start_time = datetime.now(timezone.utc)

        try:
            ws = self.websocket.create_connection(self._jetstream_url)
            print(f"[BlueSkyJetstream] Connected! Posts flowing in real time...")

            while not self._should_stop():
                try:
                    message = ws.recv()
                    if not message:
                        break

                    event = json.loads(message)
                    post = self._process_event(event)

                    if post:
                        self.posts_yielded += 1
                        yield post

                except self.websocket.WebSocketTimeoutException:
                    continue
                except json.JSONDecodeError:
                    continue

            ws.close()
            print(
                f"[BlueSkyJetstream] Done. Yielded {self.posts_yielded} posts.")

        except Exception as e:
            print(f"[BlueSkyJetstream] Error: {e}")


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("BlueSky Jetstream Source - Test")
    print("=" * 60)
    print("Connecting to live Jetstream... (Ctrl+C to stop)")
    print("-" * 60)

    try:
        source = BlueSkyJetstreamSource(
            max_posts=20,
            filter_keywords=["python", "ai", "tech"]
        )

        count = 0
        for post in source.run():
            count += 1
            print(f"\n{count}. [{post['timestamp']}] @{post['author']}")
            print(f"   {post['text'][:80]}")
            if post['hashtags']:
                print(f"   #{' #'.join(post['hashtags'][:5])}")

        print(f"\n{'=' * 60}")
        print(f"✓ Streamed {count} posts in real time.")

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Make sure you have internet connection.")
        print("Install websocket-client: pip install websocket-client")
