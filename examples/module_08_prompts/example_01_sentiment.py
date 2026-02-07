"""
Module 08, Example 1: Your First AI Agent (REAL AI VERSION)

This example demonstrates the core pattern using REAL Claude AI:
Text → AI Analysis (Prompt) → JSON → Python Logic

Network:
    Social Media Posts → [AI Sentiment Analyzer] → Results

Key Learning:
- How to use REAL Claude AI for sentiment analysis
- Compare accuracy with demo version
- Understand API costs

Time: 30-60 seconds to run | Requires ANTHROPIC_API_KEY | Costs ~$0.01
"""

import time
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (REAL VERSION - calls Claude API)
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.claude_agent import ai_transform


# ============================================================================
# STEP 1: Create Sample Data
# ============================================================================

sample_posts = ListSource(items=[
    "I love this framework! It's amazing!",
    "This is terrible service. Very disappointed.",
    "The meeting is scheduled for tomorrow at 3pm.",
    "Best day ever! So excited about the results!",
    "I'm frustrated with how long this is taking.",
    "Please send me the report when you have time.",
    "Absolutely brilliant work on the project!",
    "This is the worst experience I've had.",
    "The documentation is clear and helpful.",
    "Not sure how I feel about this change."
])

source = Source(fn=sample_posts.run, name="social_media")


# ============================================================================
# STEP 2: Create REAL AI Transform
# ============================================================================

# This is the core pattern - one line creates an AI-powered transform
# NOTE: This calls the REAL Claude API (costs money!)
ai_sentiment = ai_transform(SENTIMENT_ANALYZER)

# Wrap it in a Transform node
sentiment_node = Transform(fn=ai_sentiment, name="sentiment")


# ============================================================================
# STEP 3: Create Sink to Collect Results
# ============================================================================

results = []
collector = Sink(fn=results.append, name="collector")


# ============================================================================
# STEP 4: Build Network
# ============================================================================

g = network([
    (source, sentiment_node),
    (sentiment_node, collector)
])


# ============================================================================
# STEP 5: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 1: REAL AI-POWERED SENTIMENT ANALYSIS")
print("=" * 70)
print("\n⚠️  Using REAL Claude AI - this will cost ~$0.01")
print("Processing social media posts through Claude AI sentiment analyzer...")
print("(This may take 30-60 seconds for API calls)\n")

start_time = time.time()

g.run_network()

elapsed = time.time() - start_time


# ============================================================================
# STEP 6: Display Results
# ============================================================================

print("\n" + "=" * 70)
print("RESULTS FROM REAL AI")
print("=" * 70)

for i, result in enumerate(results, 1):
    # Get emoji based on sentiment
    sentiment_icons = {
        "POSITIVE": "😊",
        "NEGATIVE": "😞",
        "NEUTRAL": "😐"
    }
    icon = sentiment_icons.get(result["sentiment"], "📝")

    print(
        f"\n{i}. {icon} {result['sentiment']} (score: {result['score']:+.2f})")
    print(f"   Text: {result['text'][:60]}...")
    print(f"   AI Reasoning: {result['reasoning'][:80]}...")


# ============================================================================
# STEP 7: Show Summary Statistics
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY STATISTICS")
print("=" * 70)

# Count by sentiment
sentiment_counts = {}
for result in results:
    sentiment = result["sentiment"]
    sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

total = len(results)
print(f"\nTotal posts analyzed: {total}")
print(f"Processing time: {elapsed:.1f} seconds")
print(f"Average time per post: {elapsed/total:.2f} seconds")
print("\nSentiment breakdown:")
for sentiment, count in sorted(sentiment_counts.items()):
    percentage = (count / total) * 100
    print(f"  {sentiment:8}: {count} posts ({percentage:.0f}%)")

# Average sentiment score
avg_score = sum(r["score"] for r in results) / len(results)
print(f"\nAverage sentiment score: {avg_score:+.2f}")

# Estimated cost
print(f"\n💰 Estimated cost: $0.01 - $0.015")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
Used the Pattern: Text → REAL AI (Prompt) → JSON → Python Logic

1. SOURCE: Generated 10 social media posts

2. REAL AI SENTIMENT NODE:
   - Each post was sent to Claude API
   - Used SENTIMENT_ANALYZER prompt to define analysis
   - Claude returned JSON: {"sentiment": "...", "score": ..., "reasoning": "..."}
   - Notice the AI reasoning is much more sophisticated than demo!

3. PYTHON LOGIC:
   - Collected all results
   - Used JSON fields to format output
   - Calculated statistics

4. KEY DIFFERENCES FROM DEMO:
   - DEMO: Simple keyword matching (fast, free, deterministic)
   - REAL: Claude AI analysis (slower, costs money, more accurate)
   - DEMO: "Contains positive words: love, amazing"
   - REAL: "Expresses strong enthusiasm with superlative language..."
   
   Both return the SAME JSON structure!
   That's why the network code is IDENTICAL.
""")


# ============================================================================
# COMPARISON WITH DEMO
# ============================================================================

print("=" * 70)
print("DEMO vs REAL AI - SIDE BY SIDE")
print("=" * 70)
print("""
Run both versions and compare:
  python3 demo_example_01_sentiment.py  # Demo version
  python3 example_01_sentiment.py       # This (real AI)

Demo version:
  ✓ Free (no API costs)
  ✓ Fast (instant results)
  ✓ Simple keyword matching
  ✗ Less accurate on subtle sentiment
  ✗ Can't understand context or sarcasm

Real AI version:
  ✓ More accurate and nuanced
  ✓ Understands context and tone
  ✓ Handles edge cases better
  ✗ Costs money (~$0.001 per message)
  ✗ Slower (network calls)

The code is IDENTICAL except one import line!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You ran a distributed system with REAL AI!

What you learned:
- How Claude API provides sophisticated sentiment analysis
- The same pattern works for demo and real AI
- Real AI is more accurate but costs money
- JSON format is identical (demo vs real)

Compare the reasoning:
- Look at the AI reasoning in the output above
- Compare with demo version reasoning
- Notice how Claude explains its analysis

Try these experiments:
1. Add sarcastic posts and see how Claude handles them
2. Compare confidence scores with demo version
3. Add edge cases (mixed sentiment, neutral tone)

Next example: example_02_spam.py
- Real AI spam detection with Claude
- See how Claude detects subtle phishing attempts
- Compare with demo keyword matching

Cost management:
- Each message costs ~$0.001
- 10 messages = ~$0.01
- Use demo for development, real for final testing
""")

print("=" * 70 + "\n")
