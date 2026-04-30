# dissyslab/components/sinks/slack_sink.py
"""
Slack Sink — Post messages to a Slack channel via an Incoming Webhook.

No OAuth, no bot install, no scopes. You create a webhook URL in the Slack
UI, it's bound to one channel, and you POST JSON to it. One env var.

Setup (one time):
    1. Go to api.slack.com/apps → Create New App → From scratch
    2. Pick a name, pick the workspace, click Create App
    3. In the sidebar, click "Incoming Webhooks" and toggle it on
    4. Click "Add New Webhook to Workspace", pick the channel, click Allow
    5. Copy the webhook URL (looks like https://hooks.slack.com/services/T.../B.../...)
    6. Set the environment variable:
         export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'

Example office.md:
    Sinks: slack_sink

Example Python:
    from dissyslab.components.sinks.slack_sink import SlackSink
    from dissyslab.blocks import Sink

    sink = SlackSink()
    node = Sink(fn=sink.run, name="slack_alert")

Posting to a different channel:
    A webhook URL is bound to one channel at the time you create it.
    To post to a second channel, create a second webhook and a second
    SlackSink — pass webhook_url_env="SLACK_WEBHOOK_URL_ALERTS" (or
    whatever name you choose) and export that variable.
"""

import os
import requests


class SlackSink:
    """
    Send each DisSysLab message as a Slack post via an Incoming Webhook.

    Reads the webhook URL from an environment variable (default:
    SLACK_WEBHOOK_URL). The webhook is bound to one channel — set in
    the Slack UI when you create the webhook.

    The message's "text" field becomes the post body.
    If "subject" is present, it appears as a bold first line.
    If "url" is present, it appears on its own line so Slack can unfurl it.

    Args:
        webhook_url_env: Environment variable holding the webhook URL
                         (default: SLACK_WEBHOOK_URL). Override this when
                         you have multiple webhooks for different channels.
        username:        Optional display name for the post (overrides
                         the webhook's default).
        icon_emoji:      Optional emoji shortcode (e.g., ":robot_face:")
                         used as the post avatar.
        timeout:         HTTP timeout in seconds (default: 5).
    """

    def __init__(
        self,
        webhook_url_env: str = "SLACK_WEBHOOK_URL",
        username: str = None,
        icon_emoji: str = None,
        timeout: float = 5.0,
    ):
        self.webhook_url_env = webhook_url_env
        self.username = username
        self.icon_emoji = icon_emoji
        self.timeout = timeout

        self.webhook_url = os.environ.get(webhook_url_env)

        if not self.webhook_url:
            raise ValueError(
                "Slack webhook URL not found.\n"
                f"Set environment variable:\n"
                f"  export {webhook_url_env}='https://hooks.slack.com/services/...'\n"
                "Get a webhook URL at: api.slack.com/apps → your app → "
                "Incoming Webhooks → Add New Webhook to Workspace"
            )

        self.posts_sent = 0

    def _format_body(self, msg) -> str:
        """Build the Slack post body from a DisSysLab message dict."""
        text = msg.get("text", "") if isinstance(msg, dict) else ""
        if not text:
            text = str(msg)

        subject = msg.get("subject") if isinstance(msg, dict) else None
        url = msg.get("url") if isinstance(msg, dict) else None

        parts = []
        if subject:
            parts.append(f"*{subject}*")
        parts.append(text)
        if url:
            parts.append(url)
        return "\n".join(parts)

    def run(self, msg):
        """
        Called by DisSysLab for each incoming message.
        Posts the message to Slack via the configured webhook.

        Args:
            msg: Dict message from upstream DisSysLab node.
        """
        body = self._format_body(msg)

        payload = {"text": body}
        if self.username:
            payload["username"] = self.username
        if self.icon_emoji:
            payload["icon_emoji"] = self.icon_emoji

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code == 200 and response.text == "ok":
                self.posts_sent += 1
                preview = body.splitlines()[0][:60] if body else ""
                print(
                    f"[SlackSink] Sent post #{self.posts_sent}: {preview}")
            else:
                print(
                    f"[SlackSink] Slack returned {response.status_code}: "
                    f"{response.text[:200]}"
                )
        except Exception as e:
            print(f"[SlackSink] Error sending post: {e}")


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SlackSink — Test")
    print("=" * 60)
    print("Requires: SLACK_WEBHOOK_URL env var")
    print("-" * 60)

    sink = SlackSink()

    sink.run({
        "subject": "DisSysLab Test",
        "text": "This is a test message from DisSysLab SlackSink.",
        "url": "https://github.com/kmchandy/DisSysLab",
        "source": "test",
    })

    print("✓ Test complete. Check your Slack channel.")
