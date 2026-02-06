# Personal News Intelligence Dashboard

## What This Does

Builds a personalized news dashboard that:
1. Pulls articles from multiple RSS feeds
2. Summarizes each article using AI
3. Analyzes sentiment (positive/neutral/negative)
4. Clusters articles by topic
5. Displays results in a formatted console dashboard

**All transformers are built from prompts** - see `components/transformers/prompts.py`

## The Network
```
RSS Feeds → [Summarizer] → [Sentiment Analyzer] → [Topic Clusterer] → Dashboard
            (AI prompt)     (AI prompt)            (AI prompt)
```

Each transformer is a separate agent running concurrently.

## Running the Demo

**No API keys needed. No cost. Run this first.**
```bash
python network_demo.py
```

This uses prepackaged RSS articles and AI responses from `demo_data/`.

**What you'll see:**
- 20 diverse news articles (tech, politics, sports, science)
- AI-generated summaries
- Sentiment classification (mix of positive, neutral, negative)
- Topic clusters (e.g., "AI/Tech", "Politics", "Climate")
- Formatted dashboard output

## Running the Real Version

**Requires API credentials and has usage costs.**
```bash
python network_real.py
```

### Setup:

1. **RSS Feeds**: No setup needed (public feeds)

2. **Claude AI API**:
   - Sign up at https://console.anthropic.com
   - Get API key
   - Set environment variable: `export ANTHROPIC_API_KEY=your_key`
   - Note: This will cost ~$0.01-0.05 per run depending on article length

### Configuration:

Edit `network_real.py` to customize:
- RSS feed URLs (lines 10-15)
- Number of articles to fetch
- Update frequency
- Dashboard formatting

## The Transformers

All three transformers were generated from prompts:

1. **Summarizer** (`components/transformers/AI_summarizer.py`)
   - Prompt: See `prompts.py` → `NEWS_SUMMARIZER_PROMPT`
   - Takes full article → returns 2-sentence summary

2. **Sentiment Analyzer** (`components/transformers/AI_sentiment_analyzer.py`)
   - Prompt: See `prompts.py` → `SENTIMENT_ANALYZER_PROMPT`
   - Takes article → returns sentiment (positive/neutral/negative)

3. **Topic Clusterer** (`components/transformers/AI_topic_clusterer.py`)
   - Prompt: See `prompts.py` → `TOPIC_CLUSTERER_PROMPT`
   - Takes article → returns primary topic category

**Read the transformer code** to see how prompts become working agents.

## Customizing

Try modifying prompts in `prompts.py`:
- Change summary length (2 sentences → 1 sentence)
- Add emotion detection beyond sentiment
- Create different topic categories
- Add content quality scoring

Then regenerate the transformer using the new prompt.

## What's Happening Behind the Scenes

**Demo version:**
- `demo_rss_source.py` reads from `demo_data/rss_feeds.json`
- `demo_claude_agent.py` reads from `demo_data/ai_responses.json`
- No network calls, instant execution

**Real version:**
- `rss_source.py` fetches live RSS feeds
- `claude_agent.py` calls Anthropic API
- Concurrent processing of multiple articles
- Results update as feeds change
