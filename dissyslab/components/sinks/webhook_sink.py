# components/sinks/webhook_sink.py

"""
Webhook - Send HTTP POST requests to webhook URLs

This is the REAL version that sends actual HTTP requests.
Same interface as demo_webhook.py - easy to swap!

Compare with demo_webhook.py to see the demo → real pattern.
"""

import json
import time


class Webhook:
    """
    Send HTTP POST requests to webhook URLs.

    Same interface as DemoWebhook - just change the import!

    Args:
        url: Webhook URL to POST to
        headers: Optional HTTP headers dict
        timeout: Request timeout in seconds (default: 10)
        retry_count: Number of retries on failure (default: 3)
        retry_delay: Seconds between retries (default: 1)

    Common Use Cases:
        Slack: url="https://hooks.slack.com/services/..."
        Discord: url="https://discord.com/api/webhooks/..."
        Zapier: url="https://hooks.zapier.com/hooks/catch/..."
        Custom: Any HTTP endpoint

    Example:
        >>> from components.sinks.webhook_sink import Webhook
        >>> webhook = Webhook(
        ...     url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        ... )
        >>> webhook.run({"text": "Hello from DisSysLab!"})
        >>> webhook.finalize()
    """

    def __init__(
        self,
        url,
        headers=None,
        timeout=10,
        retry_count=3,
        retry_delay=1
    ):
        """
        Initialize webhook.

        Args:
            url: Webhook URL to POST to
            headers: Optional HTTP headers dict
            timeout: Request timeout in seconds (default: 10)
            retry_count: Number of retries on failure (default: 3)
            retry_delay: Seconds between retries (default: 1)
        """
        # Import here so demo version doesn't need the library
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError(
                "Webhook requires 'requests' library.\n"
                "Install it with: pip install requests"
            )

        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.post_count = 0
        self.success_count = 0
        self.failure_count = 0

        # Validate URL
        if not url.startswith("http"):
            raise ValueError(f"Invalid webhook URL: {url}")

        print(f"[Webhook] Configured for: {url}")

    def run(self, item):
        """
        Send HTTP POST to webhook.

        Args:
            item: Dict or any object to POST
        """
        # Convert item to JSON payload
        if isinstance(item, dict):
            payload = item
        else:
            payload = {"data": str(item)}

        # Send with retries
        for attempt in range(self.retry_count):
            try:
                response = self.requests.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )

                # Check response
                if response.status_code in [200, 201, 202, 204]:
                    self.post_count += 1
                    self.success_count += 1
                    print(
                        f"[Webhook] POST #{self.post_count}: Success ({response.status_code})")
                    return  # Success!
                else:
                    print(
                        f"[Webhook] POST failed: {response.status_code} {response.text[:100]}")

            except self.requests.exceptions.Timeout:
                print(
                    f"[Webhook] Timeout (attempt {attempt + 1}/{self.retry_count})")

            except self.requests.exceptions.ConnectionError as e:
                print(f"[Webhook] Connection error: {e}")

            except Exception as e:
                print(f"[Webhook] Unexpected error: {e}")

            # Retry with backoff
            if attempt < self.retry_count - 1:
                delay = self.retry_delay * (attempt + 1)
                print(f"[Webhook] Retrying in {delay}s...")
                time.sleep(delay)

        # All retries failed
        self.failure_count += 1
        print(f"[Webhook] POST failed after {self.retry_count} attempts")

    def finalize(self):
        """Report summary."""
        print(f"\n[Webhook] Summary:")
        print(f"  Total POSTs: {self.post_count}")
        print(f"  Successful: {self.success_count}")
        print(f"  Failed: {self.failure_count}")


# Test when run directly
if __name__ == "__main__":
    import os
    import sys

    print("Webhook - Test")
    print("=" * 60)

    # Check for webhook URL
    webhook_url = os.environ.get("WEBHOOK_URL")

    if not webhook_url:
        print("\n⚠️  Webhook URL not found in environment")
        print("\nTo test this, set environment variable:")
        print("  export WEBHOOK_URL='https://hooks.slack.com/services/...'")
        print("\nOr edit this file and add URL here for testing.")
        print("\nSee API_SETUP.md for Slack webhook setup instructions.")
        sys.exit(0)

    # Test: Send message
    print("\nTest: Sending webhook POST")
    print("-" * 60)

    try:
        webhook = Webhook(url=webhook_url)

        webhook.run({
            "text": "🎉 Test message from DisSysLab webhook sink!"
        })

        webhook.finalize()

        print("\n" + "=" * 60)
        print("✓ Webhook works! Check your Slack/Discord channel.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nCheck API_SETUP.md for troubleshooting.")
