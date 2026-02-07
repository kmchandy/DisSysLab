"""
Module 08, Example 3: Urgency Detection with AI (REAL AI VERSION)

This example demonstrates AI-powered urgency detection using REAL Claude AI:
Text → AI Analysis (Prompt) → JSON → Python Routing Decision

Network:
    Support Tickets → [AI Urgency Detector] → Priority Queues

Key Learning:
- How REAL Claude AI detects subtle urgency cues
- How AI understands context, tone, and implied urgency
- Multi-queue routing with sophisticated analysis

Time: 30-60 seconds to run | Requires ANTHROPIC_API_KEY | Costs ~$0.015
"""

import time
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (REAL VERSION - calls Claude API)
from components.transformers.prompts import URGENCY_DETECTOR
from components.transformers.claude_agent import ai_transform


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
# STEP 2: Create REAL AI Urgency Detector with Routing
# ============================================================================

# Create the REAL AI urgency detector
ai_urgency_detector = ai_transform(URGENCY_DETECTOR)

# Create priority queues
urgent_queue = []
normal_queue = []
low_priority_queue = []


def urgency_router(text: str):
    """
    REAL AI analyzes → Python routes to appropriate queue

    Pattern:
    - Claude AI returns: {"urgency": "HIGH/MEDIUM/LOW", "metrics": {...}, ...}
    - Python checks urgency level and metrics
    - Routes to different queues based on analysis
    """
    # REAL AI analyzes the urgency
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
    print(f"           AI Reasoning: {result['reasoning'][:60]}...")

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
print("EXAMPLE 3: REAL AI-POWERED URGENCY DETECTION & ROUTING")
print("=" * 70)
print("\n⚠️  Using REAL Claude AI - this will cost ~$0.015")
print("Processing support tickets through Claude AI urgency detector...")
print("(This may take 30-60 seconds for API calls)\n")

start_time = time.time()

g.run_network()

elapsed = time.time() - start_time


# ============================================================================
# STEP 6: Display Results by Queue
# ============================================================================

print("\n" + "=" * 70)
print("🚨 URGENT QUEUE (Requires Immediate Attention)")
print("=" * 70)

for i, ticket in enumerate(urgent_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']:.1f}/10")
    print(f"   Time-Sensitive: {ticket['metrics']['time_sensitive']}")
    print(
        f"   Immediate Action: {ticket['metrics']['requires_immediate_action']}")
    print(f"   AI Reasoning: {ticket['reasoning'][:70]}...")

print("\n" + "=" * 70)
print("⚠️  NORMAL QUEUE (Standard Priority)")
print("=" * 70)

for i, ticket in enumerate(normal_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']:.1f}/10")
    print(f"   AI Reasoning: {ticket['reasoning'][:70]}...")

print("\n" + "=" * 70)
print("✓ LOW PRIORITY QUEUE (Can Wait)")
print("=" * 70)

for i, ticket in enumerate(low_priority_queue, 1):
    print(f"\n{i}. {ticket['text'][:60]}...")
    print(f"   Urgency Score: {ticket['metrics']['urgency_score']:.1f}/10")
    print(f"   AI Reasoning: {ticket['reasoning'][:70]}...")


# ============================================================================
# STEP 7: Show Summary Statistics
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

total = len(all_results)
print(f"\nTotal tickets processed: {total}")
print(f"Processing time: {elapsed:.1f} seconds")
print(f"Average time per ticket: {elapsed/total:.2f} seconds")

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

print(f"\n💰 Estimated cost: $0.012 - $0.018")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
The Pattern: Text → REAL AI (Prompt) → JSON → Python Routing

1. SOURCE: Generated 12 support tickets with varying urgency

2. URGENCY DETECTOR NODE with REAL AI:
   - Claude AI analyzed each ticket using URGENCY_DETECTOR prompt
   - Returned JSON: {
       "urgency": "HIGH/MEDIUM/LOW",
       "metrics": {
           "urgency_score": 0-10,
           "time_sensitive": bool,
           "requires_immediate_action": bool
       },
       "reasoning": "..."
     }

3. PYTHON ROUTING LOGIC (unchanged from demo):
   The key pattern is:
   
   result = ai_urgency_detector(text)  # REAL AI analyzes
   
   if result["urgency"] == "HIGH":
       urgent_queue.append(result)     # Route to urgent
   elif result["urgency"] == "MEDIUM":
       normal_queue.append(result)     # Route to normal
   else:
       low_queue.append(result)        # Route to low priority

4. KEY DIFFERENCES FROM DEMO:
   - DEMO: Simple keyword matching ("urgent", "asap", "critical")
   - REAL: Claude understands:
     * Implied urgency (context clues)
     * Tone and emotional urgency
     * Business impact assessment
     * Temporal references and deadlines
     * Severity vs urgency distinction
""")


# ============================================================================
# COMPARISON WITH DEMO
# ============================================================================

print("=" * 70)
print("DEMO vs REAL AI - URGENCY UNDERSTANDING")
print("=" * 70)
print("""
Compare how demo vs real AI assess urgency:

Demo version:
  ✓ Counts urgency keywords
  ✓ Checks ALL CAPS and punctuation
  ✗ Misses implied urgency
  ✗ Can't assess business impact
  
Real AI version:
  ✓ Understands context and implications
  ✓ Assesses business impact
  ✓ Detects tone and emotional urgency
  ✓ Distinguishes severity from urgency
  
Example:
  Message: "Client presentation in 1 hour and slides are broken"
  
  Demo might score: MEDIUM (has "ASAP" keyword)
  Real AI scores: HIGH and explains:
    "Imminent deadline with client-facing impact creates high urgency. 
     Failure would damage client relationship and business reputation."

The contextual understanding is game-changing!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You used REAL AI for urgency detection and routing!

What you learned:
- Claude AI detects subtle urgency cues and context
- Same routing logic works with demo or real AI
- Real AI provides sophisticated business impact assessment
- Metrics help make smart triage decisions

Try these experiments:
1. Add tickets with implied urgency (no keywords)
2. Try tickets with high severity but low urgency
3. Adjust routing thresholds based on AI scores
4. Compare classification accuracy with demo version

What's next:
- Combine multiple AI agents (spam + sentiment + urgency)
- Build complete triage systems
- Add custom business logic on top of AI analysis
- Explore other prompts in the prompts library

Cost summary for all three examples:
- Example 1 (sentiment): ~$0.01
- Example 2 (spam):      ~$0.015
- Example 3 (urgency):   ~$0.015
- Total:                 ~$0.04

Real AI is worth it for production systems where accuracy matters!
""")

print("=" * 70 + "\n")
