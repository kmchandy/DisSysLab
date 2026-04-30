# dissyslab/components/sinks/webhook_sink.py
"""
Webhook Sink — POST each message to an arbitrary HTTP endpoint.

The general-purpose outbound webhook. Use it to forward messages
to any HTTP service that accepts JSON POSTs — Discord, Zapier,
Make, your own server, an inbound `webhook` source in another
DisSysLab office, anything.

For Slack specifically, prefer the `slack_sink` — it knows how to
format `subject` as a bold first line and `url` as an unfurled
link. `webhook_sink` is the unopinionated fallback.

Setup (one time):
    Option A — env var (recommended):
        export WEBHOOK_URL='https://example.com/incoming'

    Option B — pass url= directly in office.md (fine for
    non-secret URLs).

Example office.md:
    Sinks: webhook_sink                       # reads WEBHOOK_URL
    Sinks: webhook_sink(url="http://localhost:8000/webhook")
    Sinks: webhook_sink(webhook_url_env="ZAPIER_HOOK_URL")

Example Python:
    from dissyslab.components.sinks.webhook_sink import WebhookSink
    from dissyslab.blocks import Sink

    sink = WebhookSink(url="http://localhost:8000/webhook")
    node = Sink(fn=sink.run, name="webhook_out")
"""

import os
import time

import requests


class WebhookSink:
    """
    POST each DisSysLab message to an HTTP endpoint as JSON.

    The URL can be supplied in three ways, in priority order:
        1. `url=` constructor argument (explicit)
        2. `webhook_url_env=` — name of an env var holding the URL
        3. neither set → reads default env var `WEBHOOK_URL`

    The full message dict is sent as the JSON body. If the message
    is not a dict, it's wrapped as `{"data": str(msg)}`.

    Args:
        url:              Target URL. Overrides any env var.
        webhook_url_env:  Env var holding the URL (default:
                          `WEBHOOK_URL` when no explicit url is
                          given). Use this when you want to keep
                          URLs out of `office.md`.
        headers:          Optional dict of HTTP headers. Defaults
                          to `{"Content-Type": "application/json"}`.
        timeout:          Per-request timeout in seconds (default 10).
        retry_count:      Retries on failure (default 3).
        retry_delay:      Base seconds between retries; grows
                          linearly with attempt (default 1).
    """

    def __init__(
        self,
        url: str = None,
        webhook_url_env: str = None,
        headers: dict = None,
        timeout: float = 10.0,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ):
        # Resolve the URL with explicit > named env var > default env var.
        if url is not None:
            self.url = url
            self.url_source = "url= argument"
        elif webhook_url_env is not None:
            self.url = os.environ.get(webhook_url_env)
            self.url_source = f"env var {webhook_url_env}"
            if not self.url:
                raise ValueError(
                    f"Webhook URL not found.\n"
                    f"Set environment variable:\n"
                    f"  export {webhook_url_env}='https://example.com/incoming'\n"
                    f"or pass url= directly in office.md."
                )
        else:
            self.url = os.environ.get("WEBHOOK_URL")
            self.url_source = "env var WEBHOOK_URL"
            if not self.url:
                raise ValueError(
                    "Webhook URL not found.\n"
                    "Set the default environment variable:\n"
                    "  export WEBHOOK_URL='https://example.com/incoming'\n"
                    "or pass url= directly in office.md, or pass\n"
                    "webhook_url_env= to point at a different env var."
                )

        if not self.url.startswith(("http://", "https://")):
            raise ValueError(
                f"Webhook URL must start with http:// or https:// — got {self.url!r}"
            )

        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.retry_count = max(1, int(retry_count))
        self.retry_delay = float(retry_delay)

        self.posts_sent = 0
        self.posts_failed = 0

    def run(self, msg):
        """
        Called by DisSysLab for each incoming message.
        POSTs the message as JSON, retries on transient failures.
        Never raises — errors are printed and counted.
        """
        payload = msg if isinstance(msg, dict) else {"data": str(msg)}

        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                if 200 <= response.status_code < 300:
                    self.posts_sent += 1
                    print(
                        f"[WebhookSink] POST #{self.posts_sent} → "
                        f"{response.status_code}"
                    )
                    return
                # Non-2xx is treated as a soft failure; retry.
                print(
                    f"[WebhookSink] {response.status_code} from {self.url}: "
                    f"{response.text[:200]}"
                )
            except requests.exceptions.Timeout:
                print(
                    f"[WebhookSink] Timeout "
                    f"(attempt {attempt + 1}/{self.retry_count})"
                )
            except requests.exceptions.ConnectionError as e:
                print(f"[WebhookSink] Connection error: {e}")
            except Exception as e:
                print(f"[WebhookSink] Unexpected error: {e}")

            # Linear backoff before the next attempt.
            if attempt < self.retry_count - 1:
                delay = self.retry_delay * (attempt + 1)
                time.sleep(delay)

        self.posts_failed += 1
        print(f"[WebhookSink] POST failed after {self.retry_count} attempts")

    def finalize(self):
        """
        Back-compat no-op. The runtime never calls finalize() on
        sinks; older example code (examples/module_17_build_apps)
        used to call it manually. Kept so those scripts don't
        AttributeError.
        """
        print(
            f"[WebhookSink] sent={self.posts_sent} failed={self.posts_failed}"
        )


# Back-compat alias for older code that imported the class as `Webhook`.
# The constructor signature is compatible (url= still works), and
# WebhookSink also exposes finalize() as a no-op for the same reason.
Webhook = WebhookSink


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("WebhookSink — Test")
    print("=" * 60)
    print("Requires: WEBHOOK_URL env var (or pass url= directly)")
    print("-" * 60)

    sink = WebhookSink()  # uses WEBHOOK_URL

    sink.run({
        "source":    "test",
        "title":     "DisSysLab WebhookSink test",
        "text":      "If you see this, the sink works.",
        "url":       "https://github.com/kmchandy/DisSysLab",
        "timestamp": "",
    })

    print(
        f"✓ Test complete. "
        f"sent={sink.posts_sent} failed={sink.posts_failed}"
    )
