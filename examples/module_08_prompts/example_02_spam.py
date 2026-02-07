"""
Module 08, Example 2: Spam Detection with AI (REAL AI VERSION)

This example demonstrates AI-powered spam filtering using REAL Claude AI:
Text → AI Analysis (Prompt) → JSON → Python Decision (Filter or Keep)

Network:
    User Messages → [AI Spam Detector] → Filtered Results

Key Learning:
- How REAL Claude AI detects subtle spam and phishing
- How Python uses AI confidence scores for filtering
- Compare accuracy with demo keyword matching

Time: 30-60 seconds to run | Requires ANTHROPIC_API_KEY | Costs ~$0.015
"""

import time
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (REAL VERSION - calls Claude API)
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.claude_agent import ai_transform


# ============================================================================
# STEP 1: Create Sample Data
# ============================================================================

sample_messages = ListSource(items=[
    "Hey, can we schedule a meeting for tomorrow?",
    "CLICK HERE for FREE MONEY! Limited time offer!",
    "Your account has been suspended. Click link to verify.",
    "Thanks for sending the report. Looks good!",
    "BUY NOW! Act fast before this deal expires!",
    "Can you review the pull request when you get a chance?",
    "You've won the lottery! Claim your prize now!",
    "Meeting notes from today are in the shared folder.",
    "URGENT: Verify your account or it will be closed!",
    "Great presentation today. Really appreciated it.",
    "Limited time offer! Buy one get one free!!!",
    "Let me know if you have any questions about the project."
])

source = Source(fn=sample_messages.run, name="user_messages")


# ============================================================================
# STEP 2: Create REAL AI Spam Filter Transform
# ============================================================================

# First, create the REAL AI spam detector
ai_spam_detector = ai_transform(SPAM_DETECTOR)

# Then, wrap it with filtering logic


def spam_filter(text: str):
    """
    REAL AI analyzes → Python decides → Filter or keep

    Pattern:
    - Claude AI returns: {"is_spam": bool, "confidence": 0-1, ...}
    - Python checks the JSON
    - Returns None (filter) or enriched message (keep)
    """
    # REAL AI analyzes the message
    result = ai_spam_detector(text)

    # Python makes the decision based on AI's JSON output
    if result["is_spam"] and result["confidence"] > 0.7:
        # High-confidence spam → filter it out
        print(f"[FILTERED] {result['spam_type'].upper()}: {text[:50]}...")
        print(f"           AI Reason: {result['reason'][:60]}...")
        return None
    else:
        # Not spam or low confidence → keep it
        return result


# Wrap in Transform node
spam_filter_node = Transform(fn=spam_filter, name="spam_filter")


# ============================================================================
# STEP 3: Create Sink to Collect Clean Results
# ============================================================================

clean_messages = []
collector = Sink(fn=clean_messages.append, name="collector")


# ============================================================================
# STEP 4: Build Network
# ============================================================================

g = network([
    (source, spam_filter_node),
    (spam_filter_node, collector)
])


# ============================================================================
# STEP 5: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 2: REAL AI-POWERED SPAM FILTERING")
print("=" * 70)
print("\n⚠️  Using REAL Claude AI - this will cost ~$0.015")
print("Processing messages through Claude AI spam detector...")
print("(This may take 30-60 seconds for API calls)\n")

start_time = time.time()

g.run_network()

elapsed = time.time() - start_time


# ============================================================================
# STEP 6: Display Results
# ============================================================================

print("\n" + "=" * 70)
print("CLEAN MESSAGES (Spam Filtered Out by Real AI)")
print("=" * 70)

for i, result in enumerate(clean_messages, 1):
    icon = "✓"
    print(f"\n{i}. {icon} LEGITIMATE (confidence: {result['confidence']:.2f})")
    print(f"   Text: {result['text'][:60]}...")
    print(f"   AI Reason: {result['reason'][:70]}...")


# ============================================================================
# STEP 7: Show Summary Statistics
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

total_input = 12  # We know we had 12 messages
total_clean = len(clean_messages)
total_spam = total_input - total_clean

print(f"\nTotal messages processed: {total_input}")
print(f"Processing time: {elapsed:.1f} seconds")
print(f"Average time per message: {elapsed/total_input:.2f} seconds")
print(f"\nSpam filtered out: {total_spam} ({total_spam/total_input*100:.0f}%)")
print(
    f"Clean messages kept: {total_clean} ({total_clean/total_input*100:.0f}%)")

print(f"\n💰 Estimated cost: $0.012 - $0.018")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
The Pattern: Text → REAL AI (Prompt) → JSON → Python Decision

1. SOURCE: Generated 12 user messages (mix of legitimate and spam)

2. SPAM FILTER NODE with REAL AI:
   - Claude AI analyzed each message using SPAM_DETECTOR prompt
   - Returned JSON: {"is_spam": bool, "confidence": 0-1, "spam_type": "...", "reason": "..."}
   - Python checked: if is_spam AND confidence > 0.7
   - Returned None for spam (filtered out) or message dict for legitimate

3. PYTHON DECISION LOGIC (unchanged from demo):
   The key pattern is:
   
   result = ai_spam_detector(text)  # REAL AI analyzes
   
   if result["is_spam"] and result["confidence"] > 0.7:
       return None  # Filter out high-confidence spam
   else:
       return result  # Keep legitimate messages

4. KEY DIFFERENCES FROM DEMO:
   - DEMO: Keyword matching ("click here", "buy now", "free money")
   - REAL: Claude understands context, intent, and subtle manipulation
   - REAL AI can detect:
     * Sophisticated phishing attempts
     * Social engineering tactics
     * Contextual spam signals
     * New spam patterns not in keyword list
""")


# ============================================================================
# COMPARISON WITH DEMO
# ============================================================================

print("=" * 70)
print("DEMO vs REAL AI - DETECTION ACCURACY")
print("=" * 70)
print("""
Compare the reasoning between demo and real:

Demo version:
  ✓ Fast keyword matching
  ✓ Catches obvious spam
  ✗ Misses sophisticated phishing
  ✗ Can't understand context
  
Real AI version:
  ✓ Understands manipulation tactics
  ✓ Detects social engineering
  ✓ Adapts to new spam patterns
  ✓ Provides detailed reasoning
  
Example:
  Message: "Your account has been suspended. Click link to verify."
  
  Demo might say: "Contains phishing keywords"
  Real AI says: "This message uses urgency and authority to create 
                 pressure for immediate action, characteristic of 
                 phishing attempts that impersonate service providers."

The sophistication difference is dramatic!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You used REAL AI for spam filtering!

What you learned:
- Claude AI detects sophisticated spam patterns
- Same filtering logic works with demo or real AI
- Real AI provides nuanced reasoning
- Confidence scores help make better decisions

Try these experiments:
1. Add subtle phishing messages and see if Claude catches them
2. Try social engineering attempts
3. Lower confidence threshold to 0.5 (more aggressive filtering)
4. Compare false positive rates with demo version

Next example: example_03_urgency.py
- Real AI urgency detection
- See how Claude understands context and tone
- Multi-queue routing with sophisticated analysis

Cost awareness:
- This example cost ~$0.015 (12 messages)
- Real AI is worth it for production spam filtering
- Demo is fine for learning and development
""")

print("=" * 70 + "\n")
