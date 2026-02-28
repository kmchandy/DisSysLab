"""
Module 08, Example 3: Urgency Detection with AI (DEMO VERSION)

This example demonstrates AI-powered urgency detection:
Text → AI Analysis (Prompt) → JSON → Python Routing Decision

Network:
    Support Tickets → [AI Urgency Detector] → Priority Queues

Key Learning:
- How AI detects urgency and time-sensitivity
- How to use metrics from JSON for routing
- Multi-queue routing based on AI analysis

Time: 30 seconds to run | No API keys needed | Works offline
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (DEMO VERSION - no API calls)
from components.transformers.prompts import URGENCY_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_transform


# ============================================================================
# STEP 1: Create Sample Data
# ============================================================================

sample_tickets = ListSource(items=[
    "URGENT: Production server is down! Customers can't access the site!",
    "Can you update the documentation when you have time?",
    "CRITICAL: Security breach detected. Need immediate response!",
    "Quick question about the API endpoint for user profiles.",
    "Please review my code when you get a chance. No rush.",
    "ASAP: Client presentation is in 1 hour and slides are broken!",
    "The new feature looks great. Thanks for implementing it!",
    "BREAKING: Database backup failed. Data may be at risk!",
    "Let me know your thoughts on the proposal by end of week.",
    "System alert: Disk space at 95%. Act now!",
    "Reminder: Team meeting tomorrow at 10am.",
    "IMMEDIATE ACTION REQUIRED: Payment processing is failing!"
])

source = Source(fn=sample_tickets.run, name="support_tickets")


# ============================================================================
# STEP 2: Create AI Urgency Detector with Routing
# ============================================================================

# Create the AI urgency detector
ai_urgency_detector = demo_ai_transform(URGENCY_DETECTOR)

# Create priority queues
urgent_queue = []
normal_queue = []
low_priority_queue = []


def urgency_router(text: str):
    """
    AI analyzes → Python routes to appropriate queue

    Pattern:
    - AI returns: {"urgency": "HIGH/MEDIUM/LOW", "metrics": {...}, ...}
    - Python checks urgency level and metrics
    - Routes to different queues based on analysis
    """
    # AI analyzes the urgency
    result = ai_urgency_detector(text)

    urgency = result["urgency"]
    score = result["metrics"]["urgency_score"]
    immediate = result["metrics"]["requires_immediate_action"]

    # Python routing logic based on AI analysis
    if urgency == "HIGH" or immediate:
        urgent_queue.append(result)
        queue_name = "🚨 URGENT"
    elif urgency == "MEDIUM" or score >= 3:
        normal_queue.append(result)
        queue_name = "⚠️  NORMAL"
    else:
        low_priority_queue.append(result)
        queue_name = "✓ LOW"

    print(f"[{queue_name}] {text[:50]}...")

    return result


# Wrap in Transform node
urgency_node = Transform(fn=urgency_router, name="urgency_detector")


# ============================================================================
# STEP 3: Create Sink to Collect All Results
# ============================================================================

all_results = []
collector = Sink(fn=all_results.append, name="collector")


# ============================================================================
# STEP 4: Build Network
# ============================================================================

g = network([
    (source, urgency_node),
    (urgency_node, collector)
])


# ============================================================================
# STEP 5: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 3: AI-POWERED URGENCY DETECTION & ROUTING")
print("=" * 70)
print("\nProcessing support tickets through AI urgency detector...")
print("(Using demo version - no API calls)\n")

g.run_network()


# ============================================================================
# STEP 6: Display Results by Queue
# ============================================================================

print("\n" + "=" * 70)
print("🚨 URGENT QUEUE (Requires Immediate Attention)")
print("=" * 70)

for i, ticket in enumerate(urgent_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']}/10")
    print(f"   Time-Sensitive: {ticket['metrics']['time_sensitive']}")
    print(f"   Reasoning: {ticket['reasoning']}")

print("\n" + "=" * 70)
print("⚠️  NORMAL QUEUE (Standard Priority)")
print("=" * 70)

for i, ticket in enumerate(normal_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']}/10")
    print(f"   Reasoning: {ticket['reasoning']}")

print("\n" + "=" * 70)
print("✓ LOW PRIORITY QUEUE (Can Wait)")
print("=" * 70)

for i, ticket in enumerate(low_priority_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']}/10")
    print(f"   Reasoning: {ticket['reasoning']}")


# ============================================================================
# STEP 7: Show Summary Statistics
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

total = len(all_results)
print(f"\nTotal tickets processed: {total}")
print(f"\nQueue distribution:")
print(
    f"  🚨 Urgent:  {len(urgent_queue)} tickets ({len(urgent_queue)/total*100:.0f}%)")
print(
    f"  ⚠️  Normal:  {len(normal_queue)} tickets ({len(normal_queue)/total*100:.0f}%)")
print(
    f"  ✓ Low:     {len(low_priority_queue)} tickets ({len(low_priority_queue)/total*100:.0f}%)")

# Average urgency score
avg_score = sum(r["metrics"]["urgency_score"]
                for r in all_results) / len(all_results)
print(f"\nAverage urgency score: {avg_score:.1f}/10")

# Time-sensitive count
time_sensitive_count = sum(
    1 for r in all_results if r["metrics"]["time_sensitive"])
print(
    f"Time-sensitive tickets: {time_sensitive_count} ({time_sensitive_count/total*100:.0f}%)")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
The Pattern: Text → Demo AI (Prompt) → JSON → Python Routing

1. SOURCE: Generated 12 support tickets with varying urgency

2. URGENCY DETECTOR NODE:
   - AI analyzed each ticket using URGENCY_DETECTOR prompt
   - Returned JSON: {
       "urgency": "HIGH/MEDIUM/LOW",
       "metrics": {
           "urgency_score": 0-10,
           "time_sensitive": bool,
           "requires_immediate_action": bool
       },
       "reasoning": "..."
     }

3. PYTHON ROUTING LOGIC:
   The key pattern is:
   
   result = ai_urgency_detector(text)  # AI analyzes
   
   if result["urgency"] == "HIGH":
       urgent_queue.append(result)     # Route to urgent
   elif result["urgency"] == "MEDIUM":
       normal_queue.append(result)     # Route to normal
   else:
       low_queue.append(result)        # Route to low priority

4. KEY INSIGHTS:
   - AI detects urgency indicators (keywords, tone, context)
   - AI provides rich metrics (score, flags, reasoning)
   - Python uses metrics for smart routing decisions
   - Multiple queues enable prioritized processing
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You learned AI-powered routing!

What you learned:
- How AI detects urgency using URGENCY_DETECTOR prompt
- How to use metrics for routing decisions
- How to route to multiple queues based on analysis
- The routing pattern with AI

Try these experiments:
1. Add a "CRITICAL" queue for score >= 9
2. Route time_sensitive tickets differently
3. Combine urgency score with other factors
4. Add a "requires_immediate_action" filter

Next example: demo_example_04_pipeline.py
- Chain multiple AI agents (spam + urgency + sentiment)
- Build a complete triage system
- See how multiple AI analyses combine

Pattern you just learned:
    def routing_function(text):
        result = ai_function(text)      # AI analyzes
        
        if result["urgency"] == "HIGH": # Python routes
            urgent_queue.append(result)
        elif result["urgency"] == "MEDIUM":
            normal_queue.append(result)
        else:
            low_queue.append(result)
            
        return result
            
This pattern works for ANY routing task!
Use AI to analyze, Python to route.
""")

print("=" * 70)


# ============================================================================
# COMPARE: Demo vs Real
# ============================================================================

print("\n" + "=" * 70)
print("DEMO vs REAL AI")
print("=" * 70)
print("""
This demo version uses keyword matching:
- urgency_keywords = ['urgent', 'critical', 'asap', ...]
- Checks for ALL CAPS, exclamation marks
- Simple scoring system
- Fast, deterministic, free

The real AI version (using Claude):
- Understands subtle urgency cues
- Considers context and tone
- Detects implied urgency
- More nuanced scoring
- Requires API key, costs ~$0.01 for this example

Both return IDENTICAL JSON format!
Demo is perfect for learning the routing pattern.
Real AI provides more accurate urgency assessment.
""")

print("=" * 70 + "\n")
