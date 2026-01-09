# DSL Teaching Plan: Using AI to Teach Distributed Systems

## Mission Statement

**Use AI assistants with DSL to provide self-paced learning of distributed systems for first-year undergraduates through free online materials.**

Students learn by building applications they care about, progressing through modules at their own pace with AI assistance as their personal tutor.

**Note:** While examples primarily use Claude AI, students can use any AI assistant available to them (ChatGPT, Gemini, local models, etc.). The framework and teaching materials are designed to work with any capable AI assistant.

---

## Core Philosophy

Students learn distributed systems by **building applications they care about**, not by studying abstractions. The curriculum is **self-paced** - students progress through modules at their own speed. AI assistants act as teaching assistants that:
- Generates boilerplate code
- Suggests pipeline structures
- Helps debug issues
- Lets students focus on **logic**, not plumbing

---

## Design Principles

### 1. **Consistent Class-Based Pattern Throughout**
Every component follows the same pattern:
```python
class MyComponent:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
    
    def run(self, msg):  # or run() for sources
        # Process with self.param1, self.param2
        return result
```

This single pattern works for:
- **Source data objects**: `run()` returns message or None
- **Transform objects**: `run(msg)` returns transformed message or None  
- **Sink objects**: `run(msg)` returns nothing (void)
- **Router objects**: `run(msg)` returns integer index [0, N-1]

### 2. **Hide Complexity, Reveal Gradually**
- Level 1-3: Broadcast and Merge are automatic (hidden)
- Level 4: Introduce explicit Split for routing
- Level 5: Advanced patterns and custom agents

### 3. **Real Applications Drive Learning**
Every level teaches through building actual applications that students find interesting.

---

## Pedagogical Progression (Self-Paced Modules)

Students progress through modules at their own pace. Each module builds on the previous one, but students can spend as much or as little time as needed.

### **Module 1: General Graphs - Complete Social Media Analysis**

**Teaching Philosophy:** Start with a complete, real application that demonstrates all the power of the framework. Students see fanin, fanout, and parallel processing working together from day one.

**Concept:** Build a distributed system that processes social media from multiple platforms

**Structure:**
```
Twitter ↘
Reddit  → Clean → Sentiment → Archive
Facebook ↗     ↘ Urgency → Display
```

**Real Application:** "Multi-Platform Social Media Analysis System"
- Pulls posts from Twitter, Reddit, and Facebook
- Cleans text from all sources
- Analyzes sentiment and urgency in parallel
- Archives sentiment data and displays urgent items

**What Students Learn:**
- **Fanin:** Multiple sources (Twitter, Reddit, Facebook) merge into one processor (Clean)
- **Fanout:** One processor (Clean) broadcasts to multiple analyzers (Sentiment, Urgency)
- **Parallel processing:** Sentiment and urgency analysis happen independently
- **Just specify the graph:** Framework handles all the threading, message passing, merging, broadcasting
- **The `.run()` pattern:** All components use the same simple pattern

**What's Hidden (Automatic):** 
- Broadcast node (for fanout from Clean)
- Merge node (for fanin to Clean)
- Threading
- Message queues
- Synchronization

**Complete Working Example:**

```python
"""
Building a Distributed Social Media Analysis System

This demonstrates the core value of the DSL: build a distributed system
where nodes are simply ordinary Python functions - no threads, processes,
locks, or explicit message passing required.

Key Concepts:
- Fanin: Multiple sources merge into one processing node
- Fanout: One node broadcasts to multiple downstream nodes
- Message passing: Data flows automatically between nodes
"""

from dsl import network, Source, Transform, Sink
from dsl.sources import ListSource
from dsl.sinks import JSONLWriter, ListCollector

# ============================================================================
# STEP 1: Define Data Sources
# ============================================================================

class SocialMediaSource:
    """Generic social media post source"""
    def __init__(self, posts, platform):
        self.posts = posts
        self.platform = platform
        self.index = 0
    
    def run(self):
        if self.index >= len(self.posts):
            return None
        post = {
            "text": self.posts[self.index],
            "platform": self.platform
        }
        self.index += 1
        return post

# Sample data
twitter_posts = [
    "Just launched our new product! 🚀",
    "Traffic is terrible today 😤",
    "URGENT: Server down, all hands on deck!"
]

reddit_posts = [
    "Amazing coffee this morning ☕",
    "This is the worst customer service ever",
    "BREAKING: Major announcement coming"
]

facebook_posts = [
    "Love spending time with family ❤️",
    "Disappointed by the new update",
    "Emergency: Need help ASAP!"
]

# Create source objects
twitter_src = SocialMediaSource(twitter_posts, "Twitter")
reddit_src = SocialMediaSource(reddit_posts, "Reddit")
facebook_src = SocialMediaSource(facebook_posts, "Facebook")


# ============================================================================
# STEP 2: Define Processing Functions (Transforms)
# ============================================================================

class TextCleaner:
    """Remove emojis and normalize whitespace"""
    def run(self, msg):
        import re
        text = msg["text"]
        cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
        cleaned = ' '.join(cleaned.split())
        return {**msg, "clean_text": cleaned}


class SentimentAnalyzer:
    """Analyze sentiment using keyword matching"""
    def run(self, msg):
        text = msg["clean_text"].lower()
        
        positive_words = ['amazing', 'love', 'great', 'launched']
        negative_words = ['terrible', 'worst', 'disappointed', 'down']
        
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        if pos_count > neg_count:
            sentiment = "POSITIVE"
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"
        
        score = pos_count - neg_count
        return {**msg, "sentiment": sentiment, "score": score}


class UrgencyAnalyzer:
    """Detect urgent messages"""
    def run(self, msg):
        text = msg["clean_text"].lower()
        
        urgent_keywords = ['urgent', 'emergency', 'breaking', 'asap']
        is_urgent = any(keyword in text for keyword in urgent_keywords)
        
        return {**msg, "is_urgent": is_urgent}


# ============================================================================
# STEP 3: Define Output Handlers (Sinks)
# ============================================================================

class SentimentLogger:
    """Log all sentiment analysis results"""
    def run(self, msg):
        print(f"[{msg['platform']}] [{msg['sentiment']}] {msg['text'][:50]}...")


class UrgentAlerter:
    """Display urgent messages"""
    def run(self, msg):
        if msg["is_urgent"]:
            print(f"⚠️  URGENT from {msg['platform']}: {msg['clean_text']}")


# ============================================================================
# STEP 4: Build the Network
# ============================================================================

# Create agent instances
from_twitter = Source(data=twitter_src)
from_reddit = Source(data=reddit_src)
from_facebook = Source(data=facebook_src)

cleaner = TextCleaner()
clean = Transform(fn=cleaner.run)

sentiment = SentimentAnalyzer()
sentiment_analyzer = Transform(fn=sentiment.run)

urgency = UrgencyAnalyzer()
urgency_analyzer = Transform(fn=urgency.run)

sent_logger = SentimentLogger()
sentiment_sink = Sink(fn=sent_logger.run)

alert = UrgentAlerter()
urgency_sink = Sink(fn=alert.run)


# Define the graph topology
g = network([
    # Fanin: Three sources merge into clean (automatic merge)
    (from_twitter, clean),
    (from_reddit, clean),
    (from_facebook, clean),
    
    # Fanout: clean broadcasts to two analyzers (automatic broadcast)
    (clean, sentiment_analyzer),
    (clean, urgency_analyzer),
    
    # Route to different outputs
    (sentiment_analyzer, sentiment_sink),
    (urgency_analyzer, urgency_sink)
])


# ============================================================================
# STEP 5: Execute
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Multi-Platform Social Media Analysis System")
    print("=" * 70)
    print()
    
    g.run_network()
    
    print()
    print("=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
```

**What Students See:**
1. **First Day:** Here's a complete working system
2. **Then:** Let's understand each component
3. **Then:** Let's modify it to add new features
4. **Then:** Build your own with Claude AI's help

**Key Teaching Points:**
- "You just specify the graph edges - the framework does the rest"
- "Notice how Twitter, Reddit, Facebook all merge automatically into Clean"
- "Notice how Clean broadcasts automatically to both analyzers"
- "Everything runs in parallel - sentiment and urgency analysis happen simultaneously"
- "All nodes use the same `.run()` pattern"

**Student Exercises:**
1. Add a new social media platform (Instagram)
2. Add a new analyzer (spam detection)
3. Add a new output (save to file)
4. Modify sentiment keywords
5. Create a custom urgency detector

**AI Assistant's Role:**
- Explains each component
- Generates new analyzer classes when students want to add features
- Helps debug issues
- Suggests improvements
- "Want to add Instagram? Here's the code..."
- "Want to detect spam? Here's a SpamDetector class..."

---

### **Module 2: Advanced Routing and Synchronization**

**Concept:** Content-based routing and handling synchronized data streams

**This module covers two related topics:**
1. **Conditional Routing with Split** - Route messages to different handlers
2. **Local Synchronization** - Coordinate multiple data streams

**Concept:** Route messages to different handlers based on content

**Structure:**
```
Source → Split → Handler1
              ↘ Handler2
              ↘ Handler3
```

**Real Application Example:** "Content Moderation System - Route to Spam / Abuse / Safe Handlers"

**What Students Learn:**
- Content-based routing decisions
- How routers return an index to select output
- Using general N-way split (not just binary)

**New Component Introduced:** Split (explicit, not automatic)

**Example Code:**
```python
class ContentRouter:
    """Routes content to appropriate handler"""
    def __init__(self):
        self.spam_detector = SpamDetector()
        self.abuse_detector = AbuseDetector()
    
    def run(self, msg):
        if self.spam_detector.is_spam(msg["text"]):
            return 0  # Route to spam handler
        elif self.abuse_detector.is_abusive(msg["text"]):
            return 1  # Route to abuse handler
        else:
            return 2  # Route to safe content handler

class SpamHandler:
    def run(self, msg):
        print(f"SPAM: {msg['text']}")
        # Take spam action

class AbuseHandler:
    def run(self, msg):
        print(f"ABUSE: {msg['text']}")
        # Take abuse action

class SafeHandler:
    def run(self, msg):
        print(f"SAFE: {msg['text']}")
        # Process normally

# Build pipeline
router = ContentRouter()
split = Split(router=router, num_outputs=3)

spam_handler = SpamHandler()
abuse_handler = AbuseHandler()
safe_handler = SafeHandler()

g = network([
    (source, split),
    (split.out_0, spam_sink),
    (split.out_1, abuse_sink),
    (split.out_2, safe_sink)
])
```

**Why General N-way Instead of Binary:**
- Real routing decisions are rarely binary
- Same learning curve, more practical
- Students can route to 2, 3, 5, 10 outputs as needed

**AI Assistant's Role:**
- Suggests routing logic
- Generates handler classes
- Helps with classification logic

---

#### **Part 2: Local Synchronization**

**Concept:** Synchronize multiple streams using stateful transforms

**Structure:**
```
Source1 ↘
         → Merge → Synchronizer → Sink
Source2 ↗
```

**Real Application Example:** "Join User Profiles with Activity Logs"

**What Students Learn:**
- How to handle synchronized data in distributed systems
- Buffering and state management
- When and why synchronization matters
- **This teaches practical distributed systems skills**

**Key Insight:** Don't use a special MergeSynch block. Instead, teach students to implement synchronization logic themselves using stateful transforms.

**Example Code:**
```python
class ProfileActivityJoiner:
    """Synchronizes profiles with their activity logs"""
    def __init__(self):
        self.profile_buffer = {}
        self.activity_buffer = {}
    
    def run(self, msg):
        source = msg["source"]
        user_id = msg["user_id"]
        
        if source == "profile":
            self.profile_buffer[user_id] = msg
        elif source == "activity":
            if user_id not in self.activity_buffer:
                self.activity_buffer[user_id] = []
            self.activity_buffer[user_id].append(msg)
        
        # Check if we can join
        if user_id in self.profile_buffer and user_id in self.activity_buffer:
            profile = self.profile_buffer[user_id]
            activities = self.activity_buffer[user_id]
            
            # Clear buffers
            del self.profile_buffer[user_id]
            del self.activity_buffer[user_id]
            
            # Return joined data
            return {
                "user_id": user_id,
                "profile": profile,
                "activities": activities
            }
        
        # Not ready yet, filter this message
        return None

# Build pipeline
profile_source = ProfileSource()
activity_source = ActivitySource()
joiner = ProfileActivityJoiner()
reporter = ReportGenerator()

g = network([
    (profile_source, joiner_transform),
    (activity_source, joiner_transform),  # Async merge
    (joiner_transform, reporter_sink)
])
```

**Why This is Better Than MergeSynch Block:**
- Students learn to manage state themselves
- Understand buffering and flow control
- More transferable to real distributed systems
- They see **why** and **how** synchronization works

**AI Assistant's Role:**
- Suggests buffering strategies
- Generates synchronization logic
- Helps debug timing issues

---

### **Module 3: Custom Agents (Advanced)**

**Concept:** Build agents with arbitrary named ports for complex workflows

**What Students Learn:**
- Multiple named input/output ports
- Complex state machines
- Production patterns

**This is for advanced students** - most students won't need this level.

---

## Components Roadmap

### **Included from the Start:**
1. ✅ **Source** - Data generation (with `.run()` pattern)
2. ✅ **Transform** - Data transformation (with `.run(msg)` pattern)
3. ✅ **Sink** - Data consumption (with `.run(msg)` pattern)
4. ✅ **Broadcast** - Automatic fanout (hidden from students)
5. ✅ **MergeAsynch** - Automatic fanin (hidden from students)

### **Introduced at Level 4:**
6. ✅ **Split** - N-way conditional routing (with router object having `.run(msg)` returning index)

### **Deferred to Advanced Topics:**
7. ⏸️ **MergeSynch** - Synchronous merge block (teach buffering pattern instead)
8. ⏸️ **Custom Agents** - Arbitrary ports and complex logic

### **Not Included:**
9. ❌ **SplitBinary** - Too limiting, use general Split instead

---

## Implementation Status

### **Complete:**
- ✅ Source (class-based data objects with `.run()`)
- ✅ Transform (simple `fn(msg)` signature)
- ✅ Sink (simple `fn(msg)` signature)
- ✅ Example libraries for all three
- ✅ Comprehensive tests

### **To Update:**
- ⏳ Broadcast (fix STOP checking, use `broadcast_stop()`)
- ⏳ MergeAsynch (fix STOP checking)
- ⏳ graph.py (remove `params`, update to new APIs)

### **To Create:**
- 🆕 Split (general N-way router)
- 🆕 Example routers library
- 🆕 Split tests

### **To Document:**
- 📝 Level-by-level tutorials
- 📝 Real application examples
- 📝 Claude AI integration guide

---

## How AI Assistants Enhance Learning

### **1. Students Describe Their Goal**
```
Student: "I want to build a system that monitors social media for my brand. 
It should detect mentions, analyze sentiment, and alert me to negative posts."
```

### **2. AI Suggests Pipeline Structure**
```python
g = network([
    (social_source, mention_detector),
    (mention_detector, sentiment_analyzer),
    (sentiment_analyzer, priority_router),
    (priority_router.out_0, alert_sink),    # Negative
    (priority_router.out_1, archive_sink),  # Neutral  
    (priority_router.out_2, archive_sink)   # Positive
])
```

### **3. AI Generates Class Templates**
```python
class MentionDetector:
    def __init__(self, brand):
        self.brand = brand.lower()
    
    def run(self, msg):
        if self.brand in msg["text"].lower():
            return msg
        return None  # Filter out non-mentions
```

### **4. Students Customize and Learn**
- Modify templates for their use case
- Add custom logic
- Build real applications
- Learn distributed systems concepts naturally

---

## Success Metrics

### **Students Should Be Able To:**
1. Build linear data processing pipelines
2. Design multi-source, multi-sink systems
3. Implement content-based routing
4. Handle synchronization when needed
5. Use AI assistants to accelerate development
6. **Most importantly:** Build distributed applications they care about

### **Students Should Understand:**
- Message passing between nodes
- Asynchronous data flow
- Fanout and fanin patterns
- Content-based routing
- State management in distributed systems
- When and how to synchronize streams

---

## Future Enhancements

### **Additional Components (as needed):**
- Rate limiters
- Retry logic
- Error handling patterns
- Monitoring and observability
- Deployment patterns

### **Advanced Topics:**
- Custom agents with named ports
- Complex state machines
- Production best practices
- Scaling and performance

---

## Repository Structure

```
dsl/
├── README.md                    # Quick start guide
├── TEACHING_PLAN.md            # This document
├── blocks/
│   ├── source.py               # Source agent
│   ├── transform.py            # Transform agent
│   ├── sink.py                 # Sink agent
│   ├── broadcast.py            # Broadcast (fanout)
│   ├── merge.py                # MergeAsynch (fanin)
│   └── split.py                # Split (routing)
├── sources/
│   └── example_sources.py      # Library of source data objects
├── transforms/
│   └── example_transforms.py   # Library of transform functions
├── sinks/
│   └── example_sinks.py        # Library of sink functions
├── routers/
│   └── example_routers.py      # Library of routing functions
├── examples/
│   ├── module1_social_media.py     # Complete social media example
│   ├── module2_routing.py          # Content moderation with Split
│   ├── module2_synchronization.py  # Profile + activity joins
│   └── module3_custom.py           # Advanced custom agents
├── tutorials/
│   ├── module1_general_graphs.md
│   ├── module2_routing.md
│   ├── module2_synchronization.md
│   └── module3_custom_agents.md
└── tests/
    ├── test_source.py
    ├── test_transform.py
    ├── test_sink.py
    ├── test_broadcast.py
    ├── test_merge.py
    └── test_split.py
```

---

## Next Steps

1. ✅ Complete Source/Transform/Sink updates
2. ⏳ Update Broadcast and MergeAsynch
3. ⏳ Update graph.py to remove params
4. 🆕 Create Split component
5. 🆕 Create example routers library
6. 📝 Write level-by-level tutorials
7. 📝 Create Claude AI integration examples
8. 🎓 Test with first-year students!

---

**Last Updated:** January 2026
**Status:** Design phase - implementing core components