"""
Module 09, Example 2: Social Media Monitor (REAL)

Real-time social media monitoring with LIVE BlueSky stream!

Network:
    BlueSky Jetstream → [Spam Filter] → [Sentiment] → File
                                                     → Dashboard
                                                     → Webhook
    
What you'll learn:
- Live streaming from real BlueSky Jetstream
- Real-time data processing
- Production monitoring system
- Multiple outputs simultaneously

Time: 30 seconds to run | Creates actual output | Streams live data

This version connects to REAL BlueSky Jetstream WebSocket!
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components (REAL VERSION - live stream)
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.sinks.file_writer import FileWriter
from components.sinks.webhook_sink import Webhook

# For AI transforms, we'll use mock functions
# You can replace these with real AI from Module 08


# ============================================================================
# CONFIGURATION
# ============================================================================

# Streaming parameters
MAX_POSTS = 30          # Stop after 30 posts
LIFETIME = 30           # Or stop after 30 seconds
FILTER_KEYWORDS = None  # None for all posts, or ["python", "ai", "tech"]

# Output files
OUTPUT_FILE = "live_monitored_posts.json"

# Webhook URL (set to None to disable)
WEBHOOK_URL = None  # Set to your Slack/Discord webhook URL


# ============================================================================
# STEP 1: Create Source - Stream Live Posts from Jetstream
# ============================================================================

print("=" * 70)
print("EXAMPLE 2: SOCIAL MEDIA MONITOR (REAL)")
print("=" * 70)
print("\n🌐 Connecting to live BlueSky Jetstream...")
print("📡 Streaming real posts as they happen!\n")

# Connect to REAL Jetstream
jetstream = BlueSkyJetstreamSource(
    max_posts=MAX_POSTS,
    lifetime=LIFETIME,
    filter_keywords=FILTER_KEYWORDS,
    min_text_length=20,
    max_text_length=500,  # Shorter for readable dashboard
    language="en"
)

source = Source(fn=jetstream.run, name="bluesky_jetstream")


# ============================================================================
# STEP 2: Transform - Filter Spam (Mock AI)
# ============================================================================

def spam_filter(post: dict):
    """
    Filter out spam posts.

    TODO: Replace with real AI from Module 08 for better accuracy!
    """
    text = post.get("text", "").lower()

    # Simple spam detection (keywords)
    spam_keywords = ["amazing deal", "free", "click now", "don't miss",
                     "limited time", "90% off", "giveaway", "won't believe",
                     "make money", "get rich", "buy now"]

    # Check for spam indicators
    spam_score = 0
    for keyword in spam_keywords:
        if keyword in text:
            spam_score += 1

    # Also check for excessive punctuation/emojis
    if text.count("!") >= 3 or text.count("💰") >= 2 or text.count("🚀") >= 3:
        spam_score += 2

    # Filter out if spam score is high
    if spam_score >= 2:
        print(f"  [SPAM FILTERED] {post['text'][:40]}...")
        return None  # Filter out spam

    # Add spam check info to post
    post["spam_score"] = spam_score
    post["is_spam"] = False

    return post


spam_node = Transform(fn=spam_filter, name="spam_filter")


# ============================================================================
# STEP 3: Transform - Analyze Sentiment (Mock AI)
# ============================================================================

def sentiment_analyzer(post: dict):
    """
    Analyze sentiment of post.

    TODO: Replace with real AI from Module 08 for better accuracy!
    """
    text = post.get("text", "").lower()

    # Positive keywords
    positive = ["love", "amazing", "great", "excellent", "perfect", "thank",
                "excited", "happy", "wonderful", "fantastic", "awesome"]

    # Negative keywords
    negative = ["frustrated", "broken", "hate", "terrible", "awful", "bad",
                "disappointed", "angry", "annoying", "useless", "worse"]

    # Count occurrences
    pos_count = sum(1 for word in positive if word in text)
    neg_count = sum(1 for word in negative if word in text)

    # Determine sentiment
    if neg_count > pos_count:
        sentiment = "NEGATIVE"
        score = -0.7
    elif pos_count > neg_count:
        sentiment = "POSITIVE"
        score = 0.7
    else:
        sentiment = "NEUTRAL"
        score = 0.0

    # Add sentiment to post
    post["sentiment"] = sentiment
    post["sentiment_score"] = score

    return post


sentiment_node = Transform(fn=sentiment_analyzer, name="sentiment")


# ============================================================================
# STEP 4: Sink 1 - Save All Posts to File
# ============================================================================

file_writer = FileWriter(filepath=OUTPUT_FILE, format="json")
file_sink = Sink(fn=file_writer.run, name="file_output")


# ============================================================================
# STEP 5: Sink 2 - Display Live Dashboard
# ============================================================================

post_count = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}


def dashboard_display(post: dict):
    """Live dashboard showing posts as they arrive."""
    post_count["total"] += 1

    sentiment = post.get("sentiment", "NEUTRAL")
    post_count[sentiment.lower()] += 1

    # Emoji for sentiment
    emoji = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    icon = emoji.get(sentiment, "😐")

    # Display
    print(f"\n{icon} [{post_count['total']}] @{post['author']}")
    print(f"   {post['text'][:70]}...")
    print(f"   Sentiment: {sentiment} ({post['sentiment_score']:.2f})")
    print(f"   Hashtags: {post['hashtags']}")


dashboard_sink = Sink(fn=dashboard_display, name="dashboard")


# ============================================================================
# STEP 6: Sink 3 - Send Alerts for Negative Posts (Webhook)
# ============================================================================

if WEBHOOK_URL:
    webhook = Webhook(url=WEBHOOK_URL)

    def alert_negative(post: dict):
        """Send webhook alert for negative posts."""
        if post.get("sentiment") == "NEGATIVE":
            webhook.run({
                "text": f"⚠️ *Negative Post Detected*\n"
                f"Author: @{post['author']}\n"
                f"Text: {post['text'][:100]}\n"
                f"Score: {post['sentiment_score']:.2f}"
            })

    alert_sink = Sink(fn=alert_negative, name="alerts")
else:
    # No webhook - just print
    def alert_negative(post: dict):
        if post.get("sentiment") == "NEGATIVE":
            print(f"  [ALERT] Negative post detected: {post['text'][:50]}...")

    alert_sink = Sink(fn=alert_negative, name="alerts")


# ============================================================================
# STEP 7: Build Network (Fanout to 3 Sinks)
# ============================================================================

g = network([
    (source, spam_node),              # Stream → Spam Filter
    (spam_node, sentiment_node),      # Spam Filter → Sentiment
    (sentiment_node, file_sink),      # Sentiment → File (all posts)
    (sentiment_node, dashboard_sink),  # Sentiment → Dashboard (all posts)
    (sentiment_node, alert_sink)      # Sentiment → Alerts (negative only)
])


# ============================================================================
# STEP 8: Run Network
# ============================================================================

print("✅ Connected! Monitoring live posts...")
print("📊 Watch the dashboard below for real-time updates!\n")
print("-" * 70)

try:
    g.run_network()

    # Finalize outputs
    file_writer.finalize()
    if WEBHOOK_URL:
        webhook.finalize()

except KeyboardInterrupt:
    print("\n\n⚠️  Stopped by user")
    file_writer.finalize()


# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("MONITORING COMPLETE")
print("=" * 70)

print(f"\nPosts Analyzed:")
print(f"  Total: {post_count['total']}")
print(f"  Positive: {post_count['positive']} 😊")
print(f"  Negative: {post_count['negative']} 😞")
print(f"  Neutral: {post_count['neutral']} 😐")

print(f"\nOutputs:")
print(f"  ✓ All posts saved to {OUTPUT_FILE}")
print(f"  ✓ Live dashboard displayed {post_count['total']} posts")
print(f"  ✓ Sent {post_count['negative']} alerts for negative posts")

if WEBHOOK_URL:
    print(f"  ✓ Webhooks sent to {WEBHOOK_URL}")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
REAL-TIME MONITORING WITH LIVE DATA!

The Complete Flow:
1. SOURCE (Jetstream WebSocket):
   - Connected to live BlueSky Jetstream
   - Streamed REAL posts as they were published
   - Processed them in real-time

2. TRANSFORM #1 (Spam Filter):
   - Filtered spam from the live stream
   - Only passed legitimate posts forward
   - NOTE: Using mock AI - use real AI for better accuracy!

3. TRANSFORM #2 (Sentiment Analyzer):
   - Analyzed sentiment of each live post
   - Classified as POSITIVE/NEGATIVE/NEUTRAL
   - NOTE: Using mock AI - use real AI for better accuracy!

4. FANOUT to 3 SINKS:
   - File: Saved ALL posts to JSON
   - Dashboard: Displayed ALL posts live
   - Webhook: Sent alerts for NEGATIVE posts only

This is production-ready monitoring!
You just processed REAL social media data in real-time!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You built a REAL-TIME monitoring system!

What you learned:
- Streaming from live Jetstream WebSocket
- Real-time data processing
- Production monitoring architecture
- Multiple simultaneous outputs

Upgrade this system:
1. Use REAL AI (Module 08):
   - Replace mock spam filter with Claude/OpenAI
   - Replace mock sentiment with real AI
   - Much more accurate classification!

2. Add more analysis:
   - Topic classification
   - Language detection
   - Entity extraction
   - Trend detection

3. Add more outputs:
   - Database storage
   - Email alerts
   - Discord notifications
   - Real-time dashboard app

4. Customize filtering:
   - Monitor specific hashtags
   - Track your brand mentions
   - Follow competitor activity
   - Detect customer issues early

Production tips:
- Run continuously (remove max_posts/lifetime)
- Add error recovery (reconnect on disconnect)
- Store to database for long-term analysis
- Add metrics (posts/minute, sentiment trends)
- Set up alerting thresholds

Build YOUR monitoring system:
- Customer feedback tracker?
- Brand reputation monitor?
- Product review analyzer?
- News aggregator?
- Trend detector?

You have everything you need to build production systems!
""")

print("=" * 70 + "\n")
