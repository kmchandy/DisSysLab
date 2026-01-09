# DSL Implementation Plan

## Overview

This document outlines the implementation plan for the DSL (Distributed Systems Learning) framework. The goal is to enable first-year undergraduates to learn distributed systems through self-paced modules with Claude AI assistance.

---

## Mission

**Use AI assistants with DSL to provide self-paced learning of distributed systems for first-year undergraduates through free online materials.**

Students progress from simple examples with sample data to real applications with API integrations.

**Note:** Examples primarily use Claude AI, but the framework works with any AI assistant (ChatGPT, Gemini, etc.).

---

## Implementation Phases

### **Phase 1: Core Infrastructure (Highest Priority)**

**Goal:** Get the basic framework working with the new simplified APIs

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 1 | source.py | ✅ DONE | Already updated to new pattern | - |
| 2 | transform.py | ✅ DONE | Already updated to new pattern | - |
| 3 | sink.py | ✅ DONE | Already updated to new pattern | - |
| 4 | fanout.py (Broadcast) | ⏳ TODO | Fix STOP checking (`msg is STOP`), use `broadcast_stop()` | 15 min |
| 5 | fanin.py (MergeAsynch) | ⏳ TODO | Fix STOP checking (`msg is STOP`) | 10 min |
| 6 | graph.py | ⏳ TODO | Remove `params` parameter, update to new Source/Transform/Sink APIs | 60 min |
| 7 | split.py | 🆕 TODO | Finalize implementation with Pattern B (router returns list) | 30 min |

**Deliverables:**
- All core agent types working with consistent `.run()` pattern
- graph.py compiles networks without params
- Automatic fanout (Broadcast) and fanin (Merge) working
- Split node for conditional routing

**Milestone Date:** _______________

---

### **Phase 2: Example Libraries**

**Goal:** Provide ready-to-use components for common tasks

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 8 | example_sources.py | ✅ DONE | Already uses `.run()` pattern | - |
| 9 | example_transforms.py | ⏳ TODO | Change all methods to `.run(msg)` (currently .transform(), .scale(), etc.) | 30 min |
| 10 | example_sinks.py | ⏳ TODO | Change all methods to `.run(msg)` (currently .collect(), .write(), etc.) | 30 min |
| 11 | example_routers.py | 🆕 TODO | Create router library for Split (ContentRouter, SentimentRouter, etc.) | 45 min |

**Deliverables:**
- Consistent `.run()` method naming across all examples
- 4+ source examples (ListSource, RangeSource, CounterSource, FileLineSource)
- 16+ transform examples (Scaler, Counter, TextCleaner, SentimentAnalyzer, etc.)
- 8+ sink examples (ListCollector, FileWriter, JSONLWriter, StatsSink, etc.)
- 5+ router examples for Split

**Milestone Date:** _______________

---

### **Phase 3: Tests**

**Goal:** Comprehensive test coverage for all components

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 12 | test_source.py | ✅ DONE | 7 tests covering all source functionality | - |
| 13 | test_transform.py | ✅ DONE | 8 tests covering all transform functionality | - |
| 14 | test_sink.py | ✅ DONE | 8 tests covering all sink functionality | - |
| 15 | test_broadcast.py | 🆕 TODO | Test fanout with 2, 3, 5 outputs | 30 min |
| 16 | test_merge.py | 🆕 TODO | Test fanin with 2, 3, 5 inputs | 30 min |
| 17 | test_split.py | 🆕 TODO | Test routing with different router patterns | 45 min |
| 18 | test_graph.py | ⏳ TODO | Update for new APIs, test automatic broadcast/merge | 45 min |
| 19 | test_integration.py | 🆕 TODO | End-to-end tests of complete pipelines | 60 min |

**Deliverables:**
- All core components have test coverage
- Integration tests for complete pipelines
- All tests passing

**Milestone Date:** _______________

---

### **Phase 4: Module 1 - Complete Working Example**

**Goal:** Students can run a complete distributed system on day 1

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 20 | module1_social_media.py | 🆕 TODO | Complete multi-platform social media analysis with sample data | 90 min |
| 21 | module1_data.py | 🆕 TODO | Sample social media posts (Twitter, Reddit, Facebook) | 20 min |
| 22 | module1_with_apis.py | 🆕 TODO | Version with real API integration (Twitter, Reddit APIs) | 60 min |
| 23 | module1_tutorial.md | 🆕 TODO | Step-by-step tutorial explaining Module 1 | 120 min |

**Deliverables:**
- Complete working example showing fanin and fanout
- Sample data version (runs immediately, no setup)
- Real API version (for students who want real integration)
- Tutorial explaining:
  - What the system does
  - How to run it
  - How each component works
  - How to modify it
  - How to add new features

**Key Features:**
- 3 sources (Twitter, Reddit, Facebook) → automatic merge
- 1 cleaner (text processing)
- 2 analyzers (sentiment, urgency) → automatic broadcast
- 2 sinks (console display, file archive)

**Milestone Date:** _______________

---

### **Phase 5: Module 2 - Advanced Features**

**Goal:** Students learn routing and synchronization

#### **Part A: Routing**

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 24 | module2_routing.py | 🆕 TODO | Content moderation system with Split | 60 min |
| 25 | module2_routing_tutorial.md | 🆕 TODO | Tutorial on conditional routing | 90 min |

**Deliverables:**
- Content moderation example using Split
- Router that classifies content (spam, abuse, safe)
- Different handlers for each category
- Tutorial on creating custom routers

#### **Part B: Synchronization**

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 26 | module2_sync.py | 🆕 TODO | Profile + activity join example | 60 min |
| 27 | module2_sync_tutorial.md | 🆕 TODO | Tutorial on local synchronization patterns | 90 min |

**Deliverables:**
- Example joining user profiles with activity logs
- Shows buffering pattern in Transform
- Explains why/when synchronization matters
- Tutorial on implementing buffering

**Milestone Date:** _______________

---

### **Phase 6: Real API Integration Guide**

**Goal:** Help students transition from samples to real applications

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 28 | api_integration_guide.md | 🆕 TODO | Guide for adding real APIs | 120 min |
| 29 | twitter_api_example.py | 🆕 TODO | Example Twitter API integration | 45 min |
| 30 | reddit_api_example.py | 🆕 TODO | Example Reddit API integration | 45 min |
| 31 | instagram_api_example.py | 🆕 TODO | Example Instagram API integration | 45 min |
| 32 | environment_setup.md | 🆕 TODO | Guide for venv, pip, API keys | 60 min |

**Deliverables:**
- Step-by-step guide for API integration
- Example API source implementations
- Environment setup instructions (venv, pip install, .env files)
- API key management best practices
- Rate limiting patterns
- Error handling for API failures

**Topics Covered:**
1. Setting up Python virtual environment
2. Installing required libraries (`tweepy`, `praw`, `instagrape`)
3. Getting API keys/tokens
4. Storing credentials securely (.env files, not in code!)
5. Rate limiting and API quotas
6. Handling API errors gracefully
7. Testing with mock data before using real APIs

**Milestone Date:** _______________

---

### **Phase 7: Documentation**

**Goal:** Complete documentation for self-paced learning

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 33 | README.md | 🆕 TODO | Quick start guide and overview | 60 min |
| 34 | INSTALLATION.md | 🆕 TODO | Installation instructions | 30 min |
| 35 | CONCEPTS.md | 🆕 TODO | Core distributed systems concepts explained | 90 min |
| 36 | FAQ.md | 🆕 TODO | Frequently asked questions | 45 min |
| 37 | TROUBLESHOOTING.md | 🆕 TODO | Common issues and solutions | 60 min |
| 38 | AI_INTEGRATION_GUIDE.md | 🆕 TODO | How to use AI assistants effectively with DSL | 90 min |

**Deliverables:**
- Clear installation instructions
- Conceptual explanations of distributed systems
- FAQ covering common questions
- Troubleshooting guide
- Guide for using Claude AI effectively with DSL

**Milestone Date:** _______________

---

### **Phase 8: Advanced Topics (Optional)**

**Goal:** Resources for students who want to go deeper

| # | File | Status | Task | Estimated Effort |
|---|------|--------|------|-----------------|
| 39 | module3_custom_agents.py | 🆕 TODO | Example with custom agents | 90 min |
| 40 | module3_tutorial.md | 🆕 TODO | Tutorial on building custom agents | 120 min |
| 41 | advanced_patterns.md | 🆕 TODO | Advanced distributed patterns | 120 min |
| 42 | performance_guide.md | 🆕 TODO | Performance optimization tips | 90 min |

**Deliverables:**
- Custom agent examples
- Advanced patterns (circuit breakers, retry logic, etc.)
- Performance optimization guide
- Production deployment considerations

**Milestone Date:** _______________

---

## Repository Structure

```
dsl/
├── README.md                       # Phase 7
├── INSTALLATION.md                 # Phase 7
├── TEACHING_PLAN.md               # ✅ Complete
├── IMPLEMENTATION_PLAN.md         # This document
│
├── core/
│   ├── __init__.py
│   ├── core.py                    # Existing (Agent, Network)
│   └── decorators.py              # Existing (msg_map)
│
├── blocks/
│   ├── __init__.py
│   ├── source.py                  # ✅ Phase 1 - Complete
│   ├── transform.py               # ✅ Phase 1 - Complete
│   ├── sink.py                    # ✅ Phase 1 - Complete
│   ├── broadcast.py               # Phase 1
│   ├── merge.py                   # Phase 1
│   └── split.py                   # Phase 1
│
├── graph.py                       # Phase 1
│
├── sources/
│   ├── __init__.py
│   └── example_sources.py         # ✅ Phase 2 - Complete
│
├── transforms/
│   ├── __init__.py
│   └── example_transforms.py      # Phase 2
│
├── sinks/
│   ├── __init__.py
│   └── example_sinks.py          # Phase 2
│
├── routers/
│   ├── __init__.py
│   └── example_routers.py        # Phase 2
│
├── examples/
│   ├── module1/
│   │   ├── social_media.py       # Phase 4
│   │   ├── data.py               # Phase 4
│   │   └── with_apis.py          # Phase 4
│   ├── module2/
│   │   ├── routing.py            # Phase 5
│   │   └── synchronization.py   # Phase 5
│   └── module3/
│       └── custom_agents.py      # Phase 8
│
├── tutorials/
│   ├── module1_tutorial.md       # Phase 4
│   ├── module2_routing.md        # Phase 5
│   ├── module2_sync.md           # Phase 5
│   └── module3_custom.md         # Phase 8
│
├── guides/
│   ├── api_integration.md        # Phase 6
│   ├── environment_setup.md      # Phase 6
│   ├── concepts.md               # Phase 7
│   ├── ai_integration_guide.md   # Phase 7
│   ├── troubleshooting.md        # Phase 7
│   └── advanced_patterns.md      # Phase 8
│
├── api_examples/
│   ├── twitter_api.py            # Phase 6
│   ├── reddit_api.py             # Phase 6
│   └── instagram_api.py          # Phase 6
│
└── tests/
    ├── test_source.py            # ✅ Phase 3 - Complete
    ├── test_transform.py         # ✅ Phase 3 - Complete
    ├── test_sink.py              # ✅ Phase 3 - Complete
    ├── test_broadcast.py         # Phase 3
    ├── test_merge.py             # Phase 3
    ├── test_split.py             # Phase 3
    ├── test_graph.py             # Phase 3
    └── test_integration.py       # Phase 3
```

---

## Current Status Summary

### ✅ **Completed (10 items)**
- source.py, transform.py, sink.py
- example_sources.py
- test_source.py, test_transform.py, test_sink.py
- TEACHING_PLAN.md
- split.py (drafted, needs finalization)
- IMPLEMENTATION_PLAN.md (this document)

### ⏳ **In Progress (0 items)**
- (None currently)

### 🆕 **To Do (32 items)**
- Phase 1: 4 files (fanout, fanin, graph, split finalization)
- Phase 2: 3 files (update examples, create routers)
- Phase 3: 5 files (tests)
- Phase 4: 4 files (Module 1)
- Phase 5: 4 files (Module 2)
- Phase 6: 5 files (API integration)
- Phase 7: 6 files (documentation)
- Phase 8: 4 files (advanced topics)

### **Total Items:** 42
### **Completed:** 10 (24%)
### **Remaining:** 32 (76%)

---

## Effort Estimates

### **By Phase:**
- Phase 1 (Core): ~2 hours
- Phase 2 (Examples): ~2 hours
- Phase 3 (Tests): ~4 hours
- Phase 4 (Module 1): ~5 hours
- Phase 5 (Module 2): ~5 hours
- Phase 6 (API Integration): ~6 hours
- Phase 7 (Documentation): ~6 hours
- Phase 8 (Advanced): ~7 hours

### **Total Estimated Effort:** ~37 hours

### **Suggested Schedule:**
- **Week 1-2:** Phases 1-3 (Core infrastructure and tests) - 8 hours
- **Week 3:** Phase 4 (Module 1 complete) - 5 hours
- **Week 4:** Phase 5 (Module 2) - 5 hours
- **Week 5:** Phase 6 (API Integration) - 6 hours
- **Week 6:** Phase 7 (Documentation) - 6 hours
- **Week 7+:** Phase 8 (Advanced topics, as needed) - 7 hours

---

## Success Criteria

### **Minimum Viable Product (Phases 1-4):**
- ✅ Core infrastructure working
- ✅ Module 1 example runs successfully
- ✅ Students can modify and extend Module 1
- ✅ Basic documentation available

### **Full Release (Phases 1-7):**
- ✅ All modules complete
- ✅ Real API integration guide available
- ✅ Comprehensive documentation
- ✅ Students can build real applications

### **Complete Package (Phases 1-8):**
- ✅ Advanced topics covered
- ✅ Production-ready patterns
- ✅ Performance optimization guide

---

## Notes

- **Priority:** Focus on getting Module 1 working first (Phases 1-4)
- **Claude AI Integration:** Throughout development, consider how Claude AI will help students
- **Real APIs:** Design examples to work with sample data first, real APIs second
- **Testing:** Write tests as we go, not at the end
- **Documentation:** Write tutorials while building, captures fresh insights

---

## Milestone Dates

**Phase 1 Complete:** _______________  
**Phase 2 Complete:** _______________  
**Phase 3 Complete:** _______________  
**Phase 4 Complete (MVP):** _______________  
**Phase 5 Complete:** _______________  
**Phase 6 Complete:** _______________  
**Phase 7 Complete (Full Release):** _______________  
**Phase 8 Complete (Advanced):** _______________  

---

**Last Updated:** January 2026  
**Status:** Planning Phase