# test_webhook.py - SAFE VERSION
import os
from dissyslab.components.sinks.webhook_sink import Webhook

webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

if not webhook_url:
    print("Error: SLACK_WEBHOOK_URL not set")
    print("Run: export SLACK_WEBHOOK_URL='your-url-here'")
    exit(1)

webhook = Webhook(url=webhook_url)
webhook.run({"text": "🎉 Test from DisSysLab! Webhook works!"})
print("✓ Message sent! Check your Slack channel.")
