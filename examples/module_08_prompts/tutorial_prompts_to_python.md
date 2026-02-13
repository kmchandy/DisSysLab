# From Prompts to Python: Using AI in Distributed Systems

## Overview

This guide shows you how to use AI agents (powered by Claude) in your distributed systems by:
1. **Writing prompts** that define AI behavior
2. **Getting structured JSON** responses from AI
3. **Using JSON in Python** to build powerful networks

This is the core skill for building AI-powered distributed systems!

---

## The Big Picture: Three Steps

```
Step 1: Prompt           Step 2: JSON Response      Step 3: Python Usage
┌──────────────┐        ┌─────────────────────┐    ┌──────────────────┐
│ "Analyze     │   →    │ {                   │  → │ if result["is_  │
│  sentiment"  │   AI   │   "sentiment": "...",│    │    spam"]:      │
│              │        │   "score": 0.8      │    │   return None   │
└──────────────┘        │ }                   │    └──────────────────┘
                        └─────────────────────┘
```

---

## Example 1: Sentiment Analysis (Complete Walkthrough)

### Step 1: Write the Prompt

Prompts are instructions that tell the AI what to do. Good prompts:
- Are clear and specific
- Request structured output (JSON)
- Define the format exactly

```python
from components.transformers.prompts import PROMPTS

# View a prompt from the library
sentiment_prompt = PROMPTS["sentiment_analyzer"]["prompt"]
print(sentiment_prompt)
```

**Output:**
```
Analyze the sentiment of the given text.

Determine if the text expresses positive, negative, or neutral sentiment.
Provide a score from -1.0 (very negative) to +1.0 (very positive).

Return JSON format:
{
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "score": -1.0 to +1.0,
    "reasoning": "brief explanation of the sentiment"
}
```

**Key parts of a good prompt:**
- ✅ **Task definition**: "Analyze the sentiment..."
- ✅ **Instructions**: "Determine if the text expresses..."
- ✅ **Output format**: "Return JSON format: {...}"
- ✅ **Field descriptions**: What each field means

### Step 2: AI Returns Structured JSON

When you send text to the AI with this prompt, you get back JSON:

```python
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

# Create an AI agent with the sentiment analysis prompt
sentiment_agent = ClaudeAgent(get_prompt("sentiment_analyzer"))

# Send text to analyze
text = "This is the best day ever! So excited!"
result = sentiment_agent.run(text)

print(result)
```

**Output:**
```python
{
    "sentiment": "POSITIVE",
    "score": 0.9,
    "reasoning": "The text uses enthusiastic language like 'best day ever' and 'So excited' indicating strong positive emotion"
}
```

**Why JSON?**
- ✅ **Structured**: Easy to parse in Python
- ✅ **Predictable**: Same format every time
- ✅ **Type-safe**: Know what fields to expect
- ✅ **Composable**: Easy to pass between agents

### Step 3: Use JSON in Python

Now you can use this JSON like any Python dictionary:

```python
# Extract specific values
sentiment = result["sentiment"]        # "POSITIVE"
score = result["score"]                # 0.9
reasoning = result["reasoning"]        # "The text uses..."

# Make decisions based on AI output
if sentiment == "NEGATIVE" and score < -0.5:
    print("⚠️  Very negative sentiment detected!")
    send_alert()

# Transform for downstream agents
transformed = {
    "original_text": text,
    "ai_sentiment": sentiment,
    "confidence": abs(score)  # Convert to 0-1 scale
}
```

---

## Example 2: Spam Filter with Custom Logic

Here's how to combine AI JSON output with Python logic:

### The Prompt (Step 1)

```python
from components.transformers.prompts import get_prompt

spam_prompt = get_prompt("spam_detector")
# Returns a prompt that asks AI to identify spam
```

### AI Returns JSON (Step 2)

```python
from components.transformers.claude_agent import ClaudeAgent

spam_detector = ClaudeAgent(get_prompt("spam_detector"))

text = "CLICK HERE for FREE MONEY! Limited time offer!"
result = spam_detector.run(text)

print(result)
```

**Output:**
```python
{
    "is_spam": true,
    "confidence": 0.95,
    "spam_type": "promotional",
    "reason": "Contains urgency tactics and too-good-to-be-true offers"
}
```

### Use JSON in a Filter Function (Step 3)

```python
def spam_filter(text: str):
    """
    Filter function that returns None for spam, text for legitimate messages.
    
    This shows how to combine AI output with Python logic!
    """
    # Get AI analysis
    result = spam_detector.run(text)
    
    # Use JSON fields in Python logic
    is_spam = result.get("is_spam", False)
    confidence = result.get("confidence", 0.0)
    
    # Custom filtering logic
    if is_spam and confidence > 0.7:
        # High-confidence spam - filter it out
        return None
    elif is_spam and confidence > 0.4:
        # Medium confidence - flag for review
        return {"text": text, "flagged": True, "reason": result["reason"]}
    else:
        # Not spam - pass through
        return text
```

**Using in a network:**

```python
from dsl.blocks import Transform

spam_filter_node = Transform(
    fn=spam_filter,
    name="spam_filter"
)

# In your network, spam messages return None and get filtered out automatically!
```

---

## Example 3: Chaining AI Agents

You can pass JSON output from one AI agent to another:

```python
from components.transformers.prompts import get_prompt
from components.transformers.claude_agent import ClaudeAgent

# Create multiple AI agents
sentiment_agent = ClaudeAgent(get_prompt("sentiment_analyzer"))
urgency_agent = ClaudeAgent(get_prompt("urgency_detector"))

# Function that combines outputs from both agents
def analyze_and_prioritize(text: str):
    """Combines sentiment and urgency analysis."""
    
    # Get sentiment analysis (JSON)
    sentiment_result = sentiment_agent.run(text)
    
    # Get urgency analysis (JSON)
    urgency_result = urgency_agent.run(text)
    
    # Combine JSON outputs with custom logic
    priority_score = 0
    
    # Negative sentiment increases priority
    if sentiment_result["sentiment"] == "NEGATIVE":
        priority_score += abs(sentiment_result["score"]) * 3
    
    # High urgency increases priority
    if urgency_result["urgency"] == "HIGH":
        priority_score += urgency_result["metrics"]["urgency_score"]
    
    # Return combined analysis
    return {
        "text": text,
        "sentiment": sentiment_result["sentiment"],
        "urgency": urgency_result["urgency"],
        "priority_score": priority_score,
        "needs_immediate_attention": priority_score > 7
    }
```

---

## Pattern: Prompt → JSON → Python Logic

This three-step pattern is used everywhere in AI-powered systems:

### Pattern Template

```python
# STEP 1: Define what you want AI to do (Prompt)
MY_PROMPT = """
Analyze the text for [specific task].

Return JSON format:
{
    "field1": "value type",
    "field2": 0.0-1.0,
    "field3": ["list", "of", "items"]
}
"""

# STEP 2: Get AI response (JSON)
agent = ClaudeAgent(MY_PROMPT)
result = agent.run(input_text)

# STEP 3: Use JSON in Python
if result["field1"] == "some_value":
    # Your custom logic here
    do_something()
```

---

## Common JSON Patterns

### Pattern 1: Boolean Decision
```python
# Prompt asks: "Is this X?"
# JSON response: {"is_x": true/false, "confidence": 0.0-1.0}

result = agent.run(text)
if result["is_x"] and result["confidence"] > 0.8:
    handle_x_case()
```

### Pattern 2: Classification
```python
# Prompt asks: "Classify into categories"
# JSON response: {"category": "cat_name", "confidence": 0.0-1.0}

result = agent.run(text)
category = result["category"]

if category == "urgent":
    send_alert()
elif category == "normal":
    queue_for_later()
```

### Pattern 3: Scoring
```python
# Prompt asks: "Rate from -1 to +1"
# JSON response: {"score": -1.0 to +1.0, "reasoning": "..."}

result = agent.run(text)
score = result["score"]

if score > 0.5:
    positive_action()
elif score < -0.5:
    negative_action()
```

### Pattern 4: Extraction
```python
# Prompt asks: "Extract entities"
# JSON response: {"entities": ["item1", "item2", ...]}

result = agent.run(text)
entities = result["entities"]

for entity in entities:
    process_entity(entity)
```

---

## Building a Complete Network

Here's how it all comes together in a real network:

```python
# examples/ai_powered_network.py

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

# ============================================================================
# STEP 1: Create AI agents using prompts from the library
# ============================================================================

# Spam detection AI
spam_detector = ClaudeAgent(get_prompt("spam_detector"))

# Sentiment analysis AI
sentiment_analyzer = ClaudeAgent(get_prompt("sentiment_analyzer"))

# ============================================================================
# STEP 2: Wrap AI agents with custom Python logic
# ============================================================================

def filter_spam(text: str):
    """Returns None for spam, text for legitimate messages."""
    result = spam_detector.run(text)  # Get JSON
    
    # Use JSON in Python logic
    if result["is_spam"]:
        return None  # Filter out
    return text


def analyze_sentiment(text: str):
    """Returns sentiment analysis with custom fields."""
    result = sentiment_analyzer.run(text)  # Get JSON
    
    # Transform JSON for downstream processing
    return {
        "text": text,
        "sentiment": result["sentiment"],
        "score": result["score"],
        "is_positive": result["sentiment"] == "POSITIVE",
        "confidence": abs(result["score"])
    }


# ============================================================================
# STEP 3: Create transform nodes
# ============================================================================

spam_filter = Transform(fn=filter_spam, name="spam_filter")
sentiment = Transform(fn=analyze_sentiment, name="sentiment")

# ============================================================================
# STEP 4: Build network
# ============================================================================

g = network([
    (source, spam_filter),      # AI filters spam
    (spam_filter, sentiment),   # AI analyzes sentiment
    (sentiment, sink)           # Store results
])

g.run_network()
```

**Data flow:**
```
Text → AI (spam?) → JSON → Python filter → Text (no spam) →
     → AI (sentiment?) → JSON → Python transform → Enhanced JSON → Sink
```

---

## Tips for Writing Good Prompts

### ✅ DO:

1. **Be specific about the task**
   ```
   ✅ "Analyze sentiment (positive/negative/neutral) and provide a score"
   ❌ "Analyze this text"
   ```

2. **Request JSON format explicitly**
   ```
   ✅ "Return JSON format: {...}"
   ❌ "Return the results"
   ```

3. **Define all fields clearly**
   ```
   ✅ "score: 0.0-1.0 where 0 is not urgent and 1 is critical"
   ❌ "score: how urgent it is"
   ```

4. **Give examples when helpful**
   ```
   ✅ "urgency: 'HIGH' | 'MEDIUM' | 'LOW'"
   ❌ "urgency: the urgency level"
   ```

### ❌ DON'T:

1. **Don't be vague**
   ```
   ❌ "Tell me about this text"
   ✅ "Classify the topic as: technology, business, or other"
   ```

2. **Don't forget output format**
   ```
   ❌ "Analyze the sentiment"
   ✅ "Analyze the sentiment and return JSON: {sentiment: ..., score: ...}"
   ```

3. **Don't use ambiguous fields**
   ```
   ❌ "result: the result"
   ✅ "is_spam: true if spam, false otherwise"
   ```

---

## Using the Prompt Library

Instead of writing prompts from scratch, use the library:

```python
from components.transformers.prompts import (
    print_prompt_catalog,    # Browse all prompts
    search_prompts,         # Search by keyword
    get_prompt,             # Get a specific prompt
    print_prompt_details    # View prompt details
)

# Browse all available prompts
print_prompt_catalog()

# Search for prompts about spam
spam_prompts = search_prompts("spam")
print(spam_prompts.keys())

# Get a specific prompt
prompt = get_prompt("sentiment_analyzer")

# Use in your network
from components.transformers.claude_agent import ClaudeAgent
from dsl.blocks import Transform

analyzer = Transform(
    fn=ClaudeAgent(prompt).run,
    name="sentiment"
)
```

---

## Creating Custom Prompts

You can also create your own prompts:

```python
# Define your custom prompt
FORMALITY_ANALYZER_PROMPT = """Analyze the formality level of the given text.

Determine if the text is formal, casual, or mixed.

Return JSON format:
{
    "formality": "FORMAL" | "CASUAL" | "MIXED",
    "score": 0.0-1.0,
    "indicators": ["indicator1", "indicator2"],
    "reasoning": "brief explanation"
}"""

# Use it just like library prompts
from components.transformers.claude_agent import ClaudeAgent

formality_agent = ClaudeAgent(FORMALITY_ANALYZER_PROMPT)
result = formality_agent.run("Hey! What's up?")

print(result)
# {
#     "formality": "CASUAL",
#     "score": 0.9,
#     "indicators": ["informal greeting", "contraction"],
#     "reasoning": "Uses casual language and informal phrasing"
# }
```

---

## Common Patterns Summary

| Pattern | Prompt Returns | Python Uses |
|---------|----------------|-------------|
| **Filter** | `{"is_x": bool}` | `return None if is_x else text` |
| **Classify** | `{"category": str}` | `if category == "urgent": alert()` |
| **Score** | `{"score": 0-1}` | `if score > 0.8: high_priority()` |
| **Extract** | `{"items": [...]}` | `for item in items: process(item)` |
| **Transform** | `{"field1": ..., "field2": ...}` | `return {**result, "extra": custom}` |

---

## Key Takeaways

1. **Prompts define AI behavior** - Clear prompts = predictable results
2. **JSON bridges AI ↔ Python** - Structured data is easy to work with
3. **Combine AI + logic** - AI analyzes, Python decides
4. **Use the library** - 40+ prompts ready to use
5. **Experiment** - Modify prompts to fit your needs

---

## Next Steps

1. **Browse the prompt library**: `print_prompt_catalog()`
2. **Try a simple example**: Use `sentiment_analyzer` in a network
3. **Modify a prompt**: Tweak a library prompt for your needs
4. **Create custom prompts**: Build prompts for your specific tasks
5. **Chain AI agents**: Combine multiple AI analyses

**Remember:** The pattern is always the same:
```
Prompt (what to do) → JSON (structured output) → Python (custom logic)
```

Master this pattern, and you can build powerful AI-powered distributed systems! 🚀

---

## Further Reading

- **Prompt Engineering Guide**: `docs/prompt_engineering.md`
- **Prompt Library Reference**: `components/transformers/prompts.py`
- **Claude API Documentation**: https://docs.anthropic.com/
- **Example Networks**: `examples/simple_network_claude.py`