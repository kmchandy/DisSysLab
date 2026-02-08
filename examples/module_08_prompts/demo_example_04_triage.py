"""
Module 08, Example 4: Multi-Agent Customer Support Triage (DEMO VERSION)

This example demonstrates combining MULTIPLE AI agents in a pipeline:
Text → AI Spam → AI Sentiment → AI Urgency → Python Logic → Routing

Network:
    Support Messages → [Spam Filter] → [Sentiment] → [Urgency] → [Priority Calc] → Queues
                           (AI)           (AI)         (AI)        (Python)

Key Learning:
- How to chain multiple AI agents together
- How Python combines multiple AI analyses
- Complex business logic on top of AI intelligence
- Real-world customer support triage

Time: 30 seconds to run | No API keys needed | Works offline
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (DEMO VERSION - no API calls)
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_transform


# ============================================================================
# STEP 1: Create Sample Support Messages
# ============================================================================

sample_messages = ListSource(items=[
    # Critical issues - negative + urgent
    "URGENT: Our entire payment system is down! Customers can't checkout and we're losing thousands per hour!",
    "CRITICAL: Security breach - customer data may be compromised. Need immediate help!",

    # High priority - negative sentiment
    "I'm extremely frustrated. This is the third time my order has been canceled without explanation!",
    "Your service is terrible. I've been waiting 2 weeks for a refund that was promised in 3 days.",

    # Medium priority - urgent but neutral
    "Quick question: How do I reset my password? Need to access my account for a meeting in 30 minutes.",
    "Can someone help with the API documentation? Our team is blocked on this feature.",

    # Normal priority - neutral
    "What are your business hours?",
    "I'd like to update my billing information. When is convenient?",

    # Low priority - positive
    "Just wanted to say thanks for the great support last week!",
    "Love your product! Quick question about a feature when you have time.",

    # Spam - should be filtered
    "CLICK HERE for FREE premium account! Limited time offer!!!",
    "You've won a prize! Claim now or it expires!"
])

source = Source(fn=sample_messages.run, name="support_inbox")


# ============================================================================
# STEP 2: Create AI Agent Pipeline
# ============================================================================

# AI Agent 1: Spam Filter
ai_spam = demo_ai_transform(SPAM_DETECTOR)


def spam_filter(text: str):
    """Filter out spam before further processing."""
    result = ai_spam(text)
    if result["is_spam"] and result["confidence"] > 0.7:
        print(f"[SPAM FILTERED] {text[:50]}...")
        return None
    # Not spam - pass through with spam check result
    return result


spam_node = Transform(fn=spam_filter, name="spam_filter")


# AI Agent 2: Sentiment Analyzer
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)


def analyze_sentiment(msg: dict):
    """Add sentiment analysis to message."""
    result = ai_sentiment(msg["text"])
    # Merge AI sentiment into existing message
    msg["sentiment"] = result["sentiment"]
    msg["sentiment_score"] = result["score"]
    msg["sentiment_reasoning"] = result["reasoning"]
    return msg


sentiment_node = Transform(fn=analyze_sentiment, name="sentiment")


# AI Agent 3: Urgency Detector
ai_urgency = demo_ai_transform(URGENCY_DETECTOR)


def detect_urgency(msg: dict):
    """Add urgency analysis to message."""
    result = ai_urgency(msg["text"])
    # Merge AI urgency into existing message
    msg["urgency"] = result["urgency"]
    msg["urgency_score"] = result["metrics"]["urgency_score"]
    msg["time_sensitive"] = result["metrics"]["time_sensitive"]
    msg["urgency_reasoning"] = result["reasoning"]
    return msg


urgency_node = Transform(fn=detect_urgency, name="urgency")


# ============================================================================
# STEP 3: Python Business Logic - Priority Calculator
# ============================================================================

# Create priority queues
critical_queue = []
high_priority_queue = []
normal_queue = []
low_priority_queue = []


def calculate_priority_and_route(msg: dict):
    """
    Combines multiple AI analyses with business logic to calculate priority.

    This is where Python orchestrates the AI intelligence!
    """
    # Extract AI analyses
    sentiment = msg["sentiment"]
    sentiment_score = msg["sentiment_score"]
    urgency = msg["urgency"]
    urgency_score = msg["urgency_score"]
    time_sensitive = msg["time_sensitive"]

    # BUSINESS LOGIC: Calculate priority score
    priority_score = 0

    # Factor 1: Urgency contributes heavily
    if urgency == "HIGH":
        priority_score += 50
    elif urgency == "MEDIUM":
        priority_score += 25
    else:
        priority_score += 0

    # Factor 2: Negative sentiment increases priority (unhappy customers!)
    if sentiment == "NEGATIVE":
        priority_score += abs(sentiment_score) * 30  # Scale: 0-30
    elif sentiment == "POSITIVE":
        priority_score -= 10  # Lower priority for happy customers

    # Factor 3: Time sensitivity
    if time_sensitive:
        priority_score += 15

    # Factor 4: Urgency score (0-10 scale)
    priority_score += urgency_score * 2  # Scale: 0-20

    # Add priority score to message
    msg["priority_score"] = round(priority_score, 1)

    # ROUTING LOGIC: Assign to queue
    if priority_score >= 70:
        queue = "CRITICAL"
        critical_queue.append(msg)
        icon = "🚨"
    elif priority_score >= 40:
        queue = "HIGH"
        high_priority_queue.append(msg)
        icon = "⚠️"
    elif priority_score >= 20:
        queue = "NORMAL"
        normal_queue.append(msg)
        icon = "📋"
    else:
        queue = "LOW"
        low_priority_queue.append(msg)
        icon = "✓"

    msg["queue"] = queue

    print(f"[{icon} {queue:8}] Priority: {priority_score:5.1f} | {msg['text'][:40]}...")

    return msg


priority_node = Transform(
    fn=calculate_priority_and_route, name="priority_calc")


# ============================================================================
# STEP 4: Sink to Collect All Results
# ============================================================================

all_messages = []
collector = Sink(fn=all_messages.append, name="collector")


# ============================================================================
# STEP 5: Build Network - Pipeline of AI Agents
# ============================================================================

g = network([
    (source, spam_node),           # Step 1: Filter spam
    (spam_node, sentiment_node),   # Step 2: Analyze sentiment
    (sentiment_node, urgency_node),  # Step 3: Detect urgency
    (urgency_node, priority_node),  # Step 4: Calculate priority & route
    (priority_node, collector)      # Step 5: Collect results
])


# ============================================================================
# STEP 6: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 4: MULTI-AGENT CUSTOMER SUPPORT TRIAGE (DEMO)")
print("=" * 70)
print("\nCombining 3 AI agents: Spam → Sentiment → Urgency → Priority")
print("(Using demo versions - no API calls)\n")

g.run_network()


# ============================================================================
# STEP 7: Display Results by Queue
# ============================================================================

print("\n" + "=" * 70)
print("🚨 CRITICAL QUEUE (Immediate Response Required)")
print("=" * 70)

for i, msg in enumerate(critical_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")
    print(
        f"   Urgency: {msg['urgency']} (score: {msg['urgency_score']:.1f}/10)")
    print(f"   Time-Sensitive: {msg['time_sensitive']}")

print("\n" + "=" * 70)
print("⚠️  HIGH PRIORITY QUEUE (Respond Within 1 Hour)")
print("=" * 70)

for i, msg in enumerate(high_priority_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")
    print(
        f"   Urgency: {msg['urgency']} (score: {msg['urgency_score']:.1f}/10)")

print("\n" + "=" * 70)
print("📋 NORMAL QUEUE (Respond Within 24 Hours)")
print("=" * 70)

for i, msg in enumerate(normal_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")

print("\n" + "=" * 70)
print("✓ LOW PRIORITY QUEUE (Respond When Possible)")
print("=" * 70)

for i, msg in enumerate(low_priority_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")


# ============================================================================
# STEP 8: Summary Statistics
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

total = len(all_messages)
spam_filtered = 12 - total  # We started with 12 messages

print(f"\nTotal messages received: 12")
print(f"Spam filtered: {spam_filtered}")
print(f"Messages processed: {total}")

print(f"\nQueue distribution:")
print(
    f"  🚨 Critical: {len(critical_queue)} ({len(critical_queue)/total*100:.0f}%)")
print(
    f"  ⚠️  High:     {len(high_priority_queue)} ({len(high_priority_queue)/total*100:.0f}%)")
print(
    f"  📋 Normal:   {len(normal_queue)} ({len(normal_queue)/total*100:.0f}%)")
print(
    f"  ✓ Low:      {len(low_priority_queue)} ({len(low_priority_queue)/total*100:.0f}%)")

# Average priority by sentiment
print(f"\nAverage priority by sentiment:")
for sentiment_type in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
    messages = [m for m in all_messages if m["sentiment"] == sentiment_type]
    if messages:
        avg = sum(m["priority_score"] for m in messages) / len(messages)
        print(f"  {sentiment_type:8}: {avg:.1f}/100")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED - THE POWER OF COMPOSITION")
print("=" * 70)
print("""
Multiple AI Agents Working Together:

1. SPAM FILTER (AI Agent #1):
   - Analyzed each message for spam
   - Filtered out promotional content
   - Only legitimate messages proceed

2. SENTIMENT ANALYZER (AI Agent #2):
   - Analyzed emotional tone of each message
   - Added sentiment + score to message
   - Detected frustrated/angry customers

3. URGENCY DETECTOR (AI Agent #3):
   - Analyzed time-sensitivity and urgency
   - Added urgency level + metrics
   - Detected critical issues

4. PRIORITY CALCULATOR (Python Business Logic):
   - Combined all three AI analyses
   - Applied business rules:
     * High urgency + negative sentiment = CRITICAL
     * Negative sentiment alone = HIGH priority
     * Positive sentiment = LOWER priority
   - Calculated final priority score (0-100)

5. QUEUE ROUTER (Python Logic):
   - Routed to appropriate queue based on priority
   - Different SLAs for different queues

The Key Pattern:
  Message → AI Analysis #1 → AI Analysis #2 → AI Analysis #3 → Python Combines → Route

Each AI agent specializes. Python orchestrates.
This is how you build intelligent systems!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You built a multi-agent intelligent triage system!

What you learned:
- How to chain multiple AI agents in a pipeline
- How each AI agent adds intelligence (spam, sentiment, urgency)
- How Python combines multiple AI analyses
- How business logic orchestrates AI intelligence
- Real-world customer support triage pattern

Try these experiments:
1. Adjust priority calculation weights:
   - Make urgency more/less important
   - Weight negative sentiment differently
   - Add new factors (customer tier, issue type)

2. Change routing thresholds:
   - What score = critical vs high?
   - Add a "VIP" queue for important customers

3. Add more AI agents:
   - Language detector (route to appropriate team)
   - Topic classifier (route by department)
   - Customer intent (question vs complaint vs request)

4. Compare with single-agent approach:
   - Try using just one AI to do everything
   - See why specialized agents + orchestration is better

Next example: example_04_triage.py
- Same network with REAL AI
- See how Claude's sophisticated analysis improves accuracy
- Compare demo vs real triage quality

Pattern you learned:
  Multiple specialized AI agents + Python orchestration = Intelligent system

This is the foundation of production AI systems!
""")

print("=" * 70 + "\n")
