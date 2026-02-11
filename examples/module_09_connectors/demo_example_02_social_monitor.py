"""
Module 09, Example 2: Social Media Monitor (DEMO)

Real-time social media monitoring with AI analysis and multiple outputs!

Network:
    BlueSky Stream → [Spam Filter] → [Sentiment] → File
                                                  → Dashboard
                                                  → Webhook
    
What you'll learn:
- Live streaming data (not batch processing!)
- Chaining AI agents (spam → sentiment)
- Multiple outputs (fanout pattern)
- Real-time monitoring system

Time: 10 seconds to run | No setup needed | Works offline

This demo uses simulated streaming with delays to teach the pattern.
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components (DEMO VERSION - simulated stream)
from components.sources.demo_bluesky_jetstream import DemoBlueSkyJetstream
from components.sinks.demo_file_writer import DemoFileWriter
from components.sinks.demo_webhook import DemoWebhook

# For AI transforms, we'll use simple mock functions
# (In Module 08, students learn to use real AI)


# ============================================================================
# STEP 1: Create Source - Stream Live Posts
# ============================================================================

print("=" * 70)
print("EXAMPLE 2: SOCIAL MEDIA MONITOR (DEMO)")
print("=" * 70)
print("\nStreaming posts in real-time...")
print("(Demo version simulates live stream with delays)\n")

# Stream posts with simulated delays
jetstream = DemoBlueSkyJetstream(
    max_posts=15,           # Stream 15 posts
    delay_seconds=0.3       # 0.3s delay between posts (simulates real-time)
)
source = Source(fn=jetstream.run, name="bluesky_stream")


# ============================================================================
# STEP 2: Transform - Filter Spam (Mock AI)
# ============================================================================

def spam_filter(post: dict):
    """
    Filter out spam posts.

    In Module 08, you learned to use real AI for this.
    Here we use simple keyword detection as a demo.
    """
    text = post.get("text", "").lower()

    # Simple spam detection (keywords)
    spam_keywords = ["amazing deal", "free", "click now", "don't miss",
                     "limited time", "90% off", "giveaway", "won't believe"]

    # Check for spam indicators
    spam_score = 0
    for keyword in spam_keywords:
        if keyword in text:
            spam_score += 1

    # Also check for excessive punctuation/emojis
    if text.count("!") >= 3 or text.count("💰") >= 2 or text.count("🚀") >= 2:
        spam_score += 2

    # Filter out if spam score is high
    if spam_score >= 2:
        print(f"  [SPAM FILTERED] @{post['author']}: {post['text'][:40]}...")
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

    In Module 08, you learned to use real AI for this.
    Here we use simple keyword detection as a demo.
    """
    text = post.get("text", "").lower()

    # Positive keywords
    positive = ["love", "amazing", "great", "excellent", "perfect", "thank",
                "excited", "happy", "wonderful", "fantastic"]

    # Negative keywords
    negative = ["frustrated", "broken", "hate", "terrible", "awful", "bad",
                "disappointed", "angry", "annoying", "useless"]

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

file_writer = DemoFileWriter(filename="monitored_posts.json", format="json")
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

webhook = DemoWebhook(url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL")


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

print("Starting monitoring system...")
print("Watch for posts streaming in real-time!\n")
print("-" * 70)

g.run_network()

# Finalize outputs
file_writer.finalize()
webhook.finalize()


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
print(f"  ✓ All posts saved to monitored_posts.json")
print(f"  ✓ Live dashboard displayed {post_count['total']} posts")
print(f"  ✓ Sent {post_count['negative']} alerts for negative posts")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
Real-Time Monitoring System!

The Complete Flow:
1. SOURCE (Jetstream):
   - Streamed posts in real-time (simulated with delays)
   - Continuous data flow, not batch processing

2. TRANSFORM #1 (Spam Filter):
   - Checked each post for spam indicators
   - Filtered out spam (returned None)
   - Added spam_score to remaining posts

3. TRANSFORM #2 (Sentiment Analyzer):
   - Analyzed sentiment of each post
   - Added sentiment and score fields
   - Classified as POSITIVE/NEGATIVE/NEUTRAL

4. FANOUT to 3 SINKS:
   - File: Saved ALL posts for later analysis
   - Dashboard: Displayed ALL posts in real-time
   - Webhook: Sent alerts for NEGATIVE posts only

This is a production-ready monitoring pattern!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You built a real-time monitoring system!

What you learned:
- Streaming data (continuous, not batch)
- Multiple AI agents in sequence
- Fanout pattern (one input → many outputs)
- Real-time processing

Try these experiments:
1. Add more transforms:
   - Topic classifier (add topics to posts)
   - Language detector
   - Author reputation scorer

2. Add more sinks:
   - Database writer
   - Email notifications
   - Different file formats

3. Change filtering:
   - Filter by hashtags
   - Filter by sentiment threshold
   - Filter by author

4. Use real AI (Module 08):
   - Replace mock spam filter with real AI
   - Replace mock sentiment with real AI
   - Much more accurate!

Next: example_02_social_monitor.py
- Same network with REAL Jetstream
- Connects to live BlueSky stream
- Real AI analysis (if you did Module 08)
- Production monitoring system

Run it:
  python3 example_02_social_monitor.py

Then build YOUR monitoring system:
- Monitor customer feedback?
- Track brand mentions?
- Analyze product reviews?
- Build a news aggregator?

You have all the pieces now!
""")

print("=" * 70 + "\n")
