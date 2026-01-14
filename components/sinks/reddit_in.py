# dsl.connectors.reddit_in
from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional, Set

import requests


class Reddit_In:
    """
    Reddit source (JSON over HTTPS).

    • Polls a subreddit's public JSON feed (e.g., /r/python/new.json).
    • Yields one dict per post, with a small subset of useful fields.
    • In-memory dedupe by post ID so you don't reprocess the same items.
    • Simple polling loop: good for demos and teaching.

    Notes
    -----
    - This connector uses Reddit's *unauthenticated* public JSON API.
      Reddit may rate-limit or change behavior over time.
    - For anything beyond light demo use, you should read and comply with
      Reddit's API rules and consider authenticated access.

    Typical usage
    -------------
        src = Reddit_In(
            subreddit="python",
            poll_seconds=5.0,
            life_time=30.0,
            max_num_posts=50,
        )

        for post in src.run():
            print(post)
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(
        self,
        *,
        name: str | None = None,
        subreddit: str = "python",   # which subreddit to read
        sort: str = "new",           # "new", "hot", "top", etc.
        poll_seconds: float = 5.0,   # seconds between polls
        life_time: float | None = None,   # None = run indefinitely
        max_num_posts: int | None = None,  # stop after yielding N posts
        limit: int = 25,             # max posts per API call (1–100)
        user_agent: str | None = None,
    ):
        self._name = name or self.__class__.__name__
        self.subreddit = subreddit
        self.sort = sort
        self.poll_seconds = float(poll_seconds)
        self.life_time = life_time
        self.max_num_posts = (
            None if max_num_posts is None else max(0, int(max_num_posts))
        )
        self.limit = max(1, min(int(limit), 100))
        self._stop = False  # internal flag to stop iteration after max_num_posts or close()

        # Reddit strongly prefers a descriptive User-Agent
        self.user_agent = (
            user_agent
            or f"DisSysLab Reddit_In demo (subreddit={subreddit})"
        )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.user_agent,
                # Slightly more browser-like Accept can sometimes help.
                "Accept": "application/json, */*;q=0.8",
            }
        )

        # In-memory dedupe by post id
        self._seen_ids: Set[str] = set()

    @property
    def __name__(self) -> str:
        """For frameworks that read fn.__name__."""
        return self._name

    # ------------------------------------------------------------------
    # Public iteration API
    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        start = time.time()
        count = 0

        while not self._stop:
            # life timer
            if self.life_time is not None and (time.time() - start) >= self.life_time:
                break

            # fetch one page from Reddit
            posts = self._fetch_once()

            if not posts:
                # Nothing new (or fetch failed); wait and try again
                time.sleep(self.poll_seconds)
                continue

            for post in posts:
                post_id = post.get("id")
                if not post_id or post_id in self._seen_ids:
                    continue
                self._seen_ids.add(post_id)

                # Map to a compact dict in the shape your README uses
                yield {
                    "subreddit": post.get("subreddit"),
                    "author": post.get("author"),
                    "title": post.get("title"),
                    "score": post.get("score"),
                    "created_utc": post.get("created_utc"),
                    # optional extras if students want them:
                    "permalink": f"{self.BASE_URL}{post.get('permalink', '')}"
                    if post.get("permalink")
                    else None,
                    "url": post.get("url"),
                    "id": post_id,
                }

                count += 1
                if self.max_num_posts is not None and count >= self.max_num_posts:
                    self._stop = True
                    break

            if not self._stop:
                time.sleep(self.poll_seconds)

    def run(self) -> Iterator[Dict[str, Any]]:
        """
        Iterator alias, for parity with other connectors:

            for item in reddit.run():
                ...
        """
        return self.__iter__()

    def close(self) -> None:
        """Optional: signal the loop to stop early."""
        self._stop = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _fetch_once(self) -> list[dict]:
        """
        Fetch a single page of posts from the subreddit.

        Returns a list of the raw 'data' dicts for each post.
        On error, returns an empty list (iterator will just sleep and retry).
        """
        url = f"{self.BASE_URL}/r/{self.subreddit}/{self.sort}.json"
        params = {"limit": self.limit}

        try:
            resp = self._session.get(url, params=params, timeout=10.0)
            # Reddit may return 429 or other errors; just skip this cycle
            if not resp.ok:
                return []
            data = resp.json()
        except Exception:
            # Network error / JSON error; be quiet for teaching purposes
            return []

        try:
            children = data.get("data", {}).get("children", [])
            posts = [
                child.get("data", {})
                for child in children
                if isinstance(child, dict) and child.get("kind") == "t3"
            ]
            return posts
        except Exception:
            return []
