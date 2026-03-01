"""
Module 08, Example 4: Multi-Agent Customer Support Triage (REAL AI VERSION)

This example demonstrates combining MULTIPLE REAL AI agents in a pipeline:
Text → AI Spam → AI Sentiment → AI Urgency → Python Logic → Routing

Network:
    Support Messages → [Spam Filter] → [Sentiment] → [Urgency] → [Priority Calc] → Queues
                        (Claude AI)     (Claude AI)   (Claude AI)    (Python)

Key Learning:
- How sophisticated AI analysis improves triage accuracy
- How real AI understands context across multiple dimensions
- Production-ready customer support system

Time: 60-90 seconds to run | Requires ANTHROPIC_API_KEY | Costs ~$0.04-0.05
"""

import time
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (REAL VERSION - calls Claude API)
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER, URGENCY_DETECTOR
from components.transformers.claude_agent import ai_transform


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
# STEP 2: Create REAL AI Agent Pipeline
# ============================================================================

# REAL AI Agent 1: Spam Filter
ai_spam = ai_transform(SPAM_DETECTOR)


def spam_filter(text: str):
    """Filter out spam using REAL Claude AI."""
    result = ai_spam(text)
    if result["is_spam"] and result["confidence"] > 0.7:
        print(f"[SPAM FILTERED] {text[:50]}...")
        print(f"                AI Detected: {result['spam_type']}")
        return None
    # Not spam - pass through with spam check result
    return result


spam_node = Transform(fn=spam_filter, name="spam_filter")


# REAL AI Agent 2: Sentiment Analyzer
ai_sentiment = ai_transform(SENTIMENT_ANALYZER)


def analyze_sentiment(msg: dict):
    """Add REAL Claude sentiment analysis to message."""
    result = ai_sentiment(msg["text"])
    # Merge AI sentiment into existing message
    msg["sentiment"] = result["sentiment"]
    msg["sentiment_score"] = result["score"]
    msg["sentiment_reasoning"] = result["reasoning"]
    return msg


sentiment_node = Transform(fn=analyze_sentiment, name="sentiment")


# REAL AI Agent 3: Urgency Detector
ai_urgency = ai_transform(URGENCY_DETECTOR)


def detect_urgency(msg: dict):
    """Add REAL Claude urgency analysis to message."""
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
    Combines multiple REAL AI analyses with business logic.

    Python orchestrates the AI intelligence!
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
# STEP 5: Build Network - Pipeline of REAL AI Agents
# ============================================================================

g = network([
    (source, spam_node),           # Step 1: Filter spam (Claude AI)
    (spam_node, sentiment_node),   # Step 2: Analyze sentiment (Claude AI)
    (sentiment_node, urgency_node),  # Step 3: Detect urgency (Claude AI)
    (urgency_node, priority_node),  # Step 4: Calculate priority (Python)
    (priority_node, collector)      # Step 5: Collect results
])


# ============================================================================
# STEP 6: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 4: MULTI-AGENT CUSTOMER SUPPORT TRIAGE (REAL AI)")
print("=" * 70)
print("\n⚠️  Using REAL Claude AI - this will cost ~$0.04-0.05")
print("Combining 3 AI agents: Spam → Sentiment → Urgency → Priority")
print("(This may take 60-90 seconds for API calls)\n")

start_time = time.time()

# Set timeout to 120 seconds to allow for API calls to AI service.
g.run_network(timeout=120)

elapsed = time.time() - start_time


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
    print(f"   → AI: {msg['sentiment_reasoning'][:65]}...")
    print(
        f"   Urgency: {msg['urgency']} (score: {msg['urgency_score']:.1f}/10)")
    print(f"   → AI: {msg['urgency_reasoning'][:65]}...")
    print(f"   Time-Sensitive: {msg['time_sensitive']}")

print("\n" + "=" * 70)
print("⚠️  HIGH PRIORITY QUEUE (Respond Within 1 Hour)")
print("=" * 70)

for i, msg in enumerate(high_priority_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")
    print(f"   → AI: {msg['sentiment_reasoning'][:65]}...")
    print(
        f"   Urgency: {msg['urgency']} (score: {msg['urgency_score']:.1f}/10)")
    print(f"   → AI: {msg['urgency_reasoning'][:65]}...")

print("\n" + "=" * 70)
print("📋 NORMAL QUEUE (Respond Within 24 Hours)")
print("=" * 70)

for i, msg in enumerate(normal_queue, 1):
    print(f"\n{i}. Priority Score: {msg['priority_score']}/100")
    print(f"   Message: {msg['text'][:60]}...")
    print(f"   Sentiment: {msg['sentiment']} ({msg['sentiment_score']:+.2f})")
    print(
        f"   Urgency: {msg['urgency']} (score: {msg['urgency_score']:.1f}/10)")

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
print(f"Processing time: {elapsed:.1f} seconds")
print(f"Average time per message: {elapsed/total:.1f} seconds")

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

print(f"\n💰 Estimated cost: $0.04 - $0.05")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("REAL AI MULTI-AGENT INTELLIGENCE")
print("=" * 70)
print("""
Three REAL Claude AI Agents Working Together:

1. SPAM FILTER (Claude AI):
   - Sophisticated spam/phishing detection
   - Understands manipulation tactics
   - Detects social engineering

2. SENTIMENT ANALYZER (Claude AI):
   - Nuanced emotional understanding
   - Detects frustration, anger, satisfaction
   - Explains reasoning in context

3. URGENCY DETECTOR (Claude AI):
   - Understands business impact
   - Detects implied urgency (not just keywords)
   - Assesses temporal constraints

4. PRIORITY CALCULATOR (Python):
   - Same business logic as demo
   - But working with MUCH better AI analysis
   - More accurate routing decisions

5. THE POWER OF REAL AI:
   Demo version:  Simple keyword matching
   Real AI:       Contextual understanding, nuance, reasoning
   
   Result: More accurate triage, better customer experience

Notice the AI reasoning in the output above!
Claude explains WHY each message has its sentiment/urgency.
This helps support teams understand the triage decisions.
""")


# ============================================================================
# COMPARISON WITH DEMO
# ============================================================================

print("=" * 70)
print("DEMO vs REAL AI - ACCURACY COMPARISON")
print("=" * 70)
print("""
Run both versions and compare triage decisions:
  python3 demo_example_04_triage.py  # Demo version
  python3 example_04_triage.py       # This (real AI)

Key differences you'll notice:

1. SENTIMENT ANALYSIS:
   Demo: Keyword-based ("contains 'frustrated'")
   Real: Context-aware ("expresses escalating frustration due to 
          repeated service failures")

2. URGENCY DETECTION:
   Demo: Counts keywords ("urgent", "asap")
   Real: Understands business impact ("payment system down affects 
          revenue and customer trust")

3. EDGE CASES:
   Demo: May misclassify subtle messages
   Real: Handles sarcasm, implied urgency, mixed emotions

4. CONFIDENCE:
   Demo: Binary (is/isn't)
   Real: Nuanced scores with reasoning

The routing LOGIC is identical.
The AI INTELLIGENCE is dramatically better.
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS - PRODUCTION DEPLOYMENT")
print("=" * 70)
print("""
✓ You built a production-ready multi-agent triage system!

What you learned:
- How to combine multiple AI agents in a pipeline
- How real AI dramatically improves accuracy
- How Python orchestrates AI intelligence
- How to build production customer support systems

This pattern is used in real production systems!

Ideas for extension:
1. Add more AI agents:
   - Language detector → route to language-specific teams
   - Topic classifier → route by department (billing, technical, etc)
   - Customer intent → question vs complaint vs feature request

2. Add non-AI transforms:
   - Customer tier lookup (VIP customers get higher priority)
   - Historical context (repeated issues get escalated)
   - Business hours routing (after-hours → on-call team)

3. Add memory/state:
   - Track customer conversation history
   - Escalate if same customer contacts multiple times
   - Learn from agent feedback on triage quality

4. Optimize costs:
   - Use demo AI for initial filter
   - Use real AI only for ambiguous cases
   - Cache common queries

Real-world deployment considerations:
- Monitor triage accuracy (track misrouted messages)
- A/B test priority calculation weights
- Collect feedback from support agents
- Measure impact on customer satisfaction

Cost summary:
- Demo version:  $0 (free)
- Real version:  ~$0.04-0.05 per 10 messages
- For 1000 messages/day: ~$4-5/day = ~$150/month

Worth it? Compare to cost of poor customer support!
""")

print("=" * 70 + "\n")
