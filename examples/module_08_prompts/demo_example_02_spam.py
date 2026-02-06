"""
Module 08, Example 2: Spam Detection with AI (DEMO VERSION)

This example demonstrates AI-powered spam filtering:
Text → AI Analysis (Prompt) → JSON → Python Decision (Filter or Keep)

Network:
    User Messages → [AI Spam Detector] → Filtered Results

Key Learning:
- How AI detects spam patterns
- How Python uses JSON to make filtering decisions
- The filtering pattern: return None to filter out

Time: 30 seconds to run | No API keys needed | Works offline
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (DEMO VERSION - no API calls)
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_transform


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
# STEP 2: Create AI Spam Filter Transform
# ============================================================================

# First, create the AI spam detector
ai_spam_detector = demo_ai_transform(SPAM_DETECTOR)

# Then, wrap it with filtering logic


def spam_filter(text: str):
    """
    AI analyzes → Python decides → Filter or keep

    Pattern:
    - AI returns: {"is_spam": bool, "confidence": 0-1, ...}
    - Python checks the JSON
    - Returns None (filter) or text (keep)
    """
    # AI analyzes the message
    result = ai_spam_detector(text)

    # Python makes the decision based on AI's JSON output
    if result["is_spam"] and result["confidence"] > 0.7:
        # High-confidence spam → filter it out
        print(f"[FILTERED] {result['spam_type'].upper()}: {text[:50]}...")
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
print("EXAMPLE 2: AI-POWERED SPAM FILTERING")
print("=" * 70)
print("\nProcessing messages through AI spam detector...")
print("(Using demo version - no API calls)\n")

g.run_network()


# ============================================================================
# STEP 6: Display Results
# ============================================================================

print("\n" + "=" * 70)
print("CLEAN MESSAGES (Spam Filtered Out)")
print("=" * 70)

for i, result in enumerate(clean_messages, 1):
    icon = "✓"
    print(f"\n{i}. {icon} LEGITIMATE")
    print(f"   Text: {result['text'][:60]}...")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Reason: {result['reason']}")


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
print(f"Spam filtered out: {total_spam} ({total_spam/total_input*100:.0f}%)")
print(
    f"Clean messages kept: {total_clean} ({total_clean/total_input*100:.0f}%)")

# Breakdown by spam type (for filtered messages)
print("\nFiltered spam types:")
print("  - Promotional/Marketing")
print("  - Phishing attempts")
print("  - Scams")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
The Pattern: Text → Demo AI (Prompt) → JSON → Python Decision

1. SOURCE: Generated 12 user messages (mix of legitimate and spam)

2. SPAM FILTER NODE:
   - AI analyzed each message using SPAM_DETECTOR prompt
   - Returned JSON: {"is_spam": bool, "confidence": 0-1, "spam_type": "...", "reason": "..."}
   - Python checked: if is_spam AND confidence > 0.7
   - Returned None for spam (filtered out) or message dict for legitimate

3. PYTHON DECISION LOGIC:
   The key pattern is:
   
   result = ai_spam_detector(text)  # AI analyzes
   
   if result["is_spam"] and result["confidence"] > 0.7:
       return None  # Filter out high-confidence spam
   else:
       return result  # Keep legitimate messages

4. KEY INSIGHT:
   - AI provides intelligence (spam detection)
   - Python provides judgment (confidence threshold, filtering decision)
   - Returning None removes message from pipeline
   - This is the FILTERING PATTERN
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You learned the filtering pattern with AI!

What you learned:
- How AI detects spam using SPAM_DETECTOR prompt
- How to use confidence scores in decisions
- The filtering pattern: return None to remove messages
- How AI + Python logic work together

Try these experiments:
1. Change confidence threshold: if confidence > 0.5 (more aggressive)
2. Add a "suspicious" category for medium confidence (0.5-0.7)
3. Count how many of each spam_type were filtered
4. Create a "quarantine" list instead of filtering completely

Next example: demo_example_03_pipeline.py
- Chain TWO AI agents: spam filter → sentiment analyzer
- See how AI agents compose in pipelines
- Build more complex filtering logic

Pattern you just learned:
    def filter_function(text):
        result = ai_function(text)  # AI analyzes
        if result["some_field"]:    # Python decides
            return None             # Filter out
        else:
            return result           # Keep it
            
This pattern works for ANY filtering task!
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
- spam_keywords = ['click here', 'buy now', 'free money', ...]
- Checks for ALL CAPS, excessive punctuation
- Fast, deterministic, free

The real AI version (using Claude):
- Understands context and intent
- Detects subtle phishing attempts
- Recognizes new spam patterns
- More accurate on edge cases
- Requires API key, costs ~$0.01 for this example

Both return IDENTICAL JSON format!
Demo is perfect for learning the pattern.
Real AI is for production spam filtering.
""")

print("=" * 70 + "\n")
