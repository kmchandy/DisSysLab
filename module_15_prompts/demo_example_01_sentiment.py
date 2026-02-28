"""
Module 08, Example 1: Your First AI Agent (DEMO VERSION)

This example demonstrates the core pattern:
Text → AI Analysis (Prompt) → JSON → Python Logic

Network:
    Social Media Posts → [AI Sentiment Analyzer] → Results

Key Learning:
- How to use prompts from the library
- How AI returns structured JSON
- How Python uses JSON to make decisions

Time: 30 seconds to run | No API keys needed | Works offline
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components (DEMO VERSION - no API calls)
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_transform


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
# STEP 2: Create Demo AI Transform
# ============================================================================

# This is the core pattern - one line creates an AI-powered transform
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)

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
print("EXAMPLE 1: DEMO_AI-POWERED SENTIMENT ANALYSIS")
print("=" * 70)
print("\nProcessing social media posts through AI sentiment analyzer...")
print("(Using demo version, not calls to AI - no API calls)\n")

g.run_network()


# ============================================================================
# STEP 6: Display Results
# ============================================================================

print("\n" + "=" * 70)
print("RESULTS")
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
    print(f"   Reasoning: {result['reasoning']}")


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
print("\nSentiment breakdown:")
for sentiment, count in sorted(sentiment_counts.items()):
    percentage = (count / total) * 100
    print(f"  {sentiment:8}: {count} posts ({percentage:.0f}%)")

# Average sentiment score
avg_score = sum(r["score"] for r in results) / len(results)
print(f"\nAverage sentiment score: {avg_score:+.2f}")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
Used the Pattern: Text → Demo AI (Prompt) → JSON → Python Logic

1. SOURCE: Generated 10 social media posts

2. AI SENTIMENT NODE:
   - Received each post as text
   - Used SENTIMENT_ANALYZER prompt to define analysis
   - Returned JSON: {"sentiment": "...", "score": ..., "reasoning": "..."}

3. PYTHON LOGIC:
   - Collected all results
   - Used JSON fields to format output
   - Calculated statistics

4. KEY INSIGHT:
   - Demo AI does the analysis (sentiment detection)
   - Python does the logic (statistics, formatting, decisions)
   - Prompt defines what AI analyzes
   - JSON bridges AI output to Python code

This is the same pattern for ALL AI agents.
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You ran a distributed system with demo AI agents.

What you learned:
- How to use prompts from the library (SENTIMENT_ANALYZER), replace by real AI later
- How AI returns structured JSON
- How Python processes JSON to make decisions
- The core pattern: Prompt → JSON → Python Logic

Try these experiments:
1. Add more posts to sample_posts
2. Print just the positive posts: if result["sentiment"] == "POSITIVE"
3. Filter by score: if result["score"] > 0.5
4. Change the network to filter negative posts (return None)

Next example: demo_example_02_pipeline.py
- Learn how to chain multiple AI agents
- Build a spam filter + sentiment analyzer pipeline
- See how AI agents compose naturally

To see the REAL AI version (requires API key):
- Open: example_01_sentiment.py
- Same code, just imports from claude_agent instead of demo_ai_agent
- See how demo → real is just one line change
""")

print("=" * 70)


# ============================================================================
# COMPARE: Demo vs Real
# ============================================================================

print("\n" + "=" * 70)
print("DEMO vs REAL AI")
print("=" * 70)
print("""
This demo version uses simple keyword matching:
- positive_words = ['love', 'great', 'amazing', ...]
- Fast, deterministic, free

The real AI version (claude_agent.py):
- Uses Claude API for nuanced analysis
- Understands context, sarcasm, subtle sentiment
- More accurate, handles edge cases better
- Requires API key and costs ~$0.01 for this example

Both return IDENTICAL JSON format, so the network code is the same!

Demo is perfect for learning. Real AI is for production.
""")

print("=" * 70 + "\n")
