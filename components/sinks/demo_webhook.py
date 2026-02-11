# components/sinks/demo_webhook.py

"""
Demo Webhook - Show what would be POSTed to webhook URL

This demo version prints to console instead of sending HTTP requests.
Perfect for learning without needing actual webhook URLs!

Compare with webhook_sink.py to see the demo → real pattern.
"""

import json


class DemoWebhook:
    """
    Demo webhook - prints instead of POSTing.

    Shows what would be sent to webhook URL without actual HTTP requests.
    Perfect for learning the webhook pattern.

    Args:
        url: Webhook URL to simulate (not actually called)
        headers: Optional HTTP headers dict

    Example:
        >>> from components.sinks.demo_webhook import DemoWebhook
        >>> webhook = DemoWebhook(url="https://hooks.slack.com/...")
        >>> webhook.run({"text": "Hello from DisSysLab!"})
        >>> webhook.finalize()
    """

    def __init__(self, url, headers=None):
        """
        Initialize demo webhook.

        Args:
            url: Webhook URL to simulate (not actually called)
            headers: Optional HTTP headers dict
        """
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.post_count = 0

        print(f"[DemoWebhook] Would POST to: {url}")
        if headers:
            print(f"[DemoWebhook] Headers: {headers}")

    def run(self, item):
        """
        Display what would be POSTed.

        Args:
            item: Dict or any object to POST
        """
        self.post_count += 1

        # Convert item to JSON payload
        if isinstance(item, dict):
            payload = item
        else:
            payload = {"data": str(item)}

        # Display
        print("\n" + "=" * 70)
        print(f"WEBHOOK POST #{self.post_count} (would be sent)")
        print("=" * 70)
        print(f"POST {self.url}")

        if self.headers:
            print("\nHeaders:")
            for key, value in self.headers.items():
                print(f"  {key}: {value}")

        print("\nJSON Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("=" * 70)

    def finalize(self):
        """Summary of what would have been sent."""
        print(
            f"\n[DemoWebhook] Would have sent {self.post_count} POST requests")


# Test when run directly
if __name__ == "__main__":
    print("Demo Webhook - Test")
    print("=" * 70)

    # Test 1: Simple message
    print("\nTest 1: Simple Slack Message")
    print("-" * 70)
    webhook = DemoWebhook(url="https://hooks.slack.com/services/T00/B00/XXX")
    webhook.run({
        "text": "🚨 Alert: Server CPU at 95%"
    })

    # Test 2: Formatted message
    print("\n\nTest 2: Formatted Message")
    print("-" * 70)
    webhook.run({
        "text": "*ALERT*\nServer: production-1\nCPU: 95%\nMemory: 87%",
        "username": "MonitorBot",
        "icon_emoji": ":chart_with_upwards_trend:"
    })

    # Test 3: Custom data
    print("\n\nTest 3: Custom Event Data")
    print("-" * 70)
    webhook.run({
        "event": "user_signup",
        "user_id": 12345,
        "email": "user@example.com",
        "timestamp": "2026-02-08T10:30:00Z"
    })

    webhook.finalize()

    print("\n" + "=" * 70)
    print("✓ Demo Webhook works!")
