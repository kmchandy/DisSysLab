# Module 2: AI Integration

*Your first real-world AI-powered distributed system.*

In Module 1 you built a pipeline with mock components — keyword-based spam detection, simulated sentiment analysis, fake RSS data. It worked, and you learned the pattern. Now you're going to do the same thing with real data and real AI. The generated code will look almost identical. The results will be dramatically better.

This module uses **BlueSky** (a free social media platform) as a live data source and **Claude AI** for real sentiment analysis and entity extraction. Your app will monitor real posts from real people in real time, analyze them with real AI, and save the results to a real file. The mock-to-real swap is exactly what Module 1 promised: same architecture, different components.

---

## Part 1: Setup (10 minutes)

You need two things: an Anthropic API key and the component files in your Claude Project.

### Get Your Anthropic API Key

You already have a Claude account from Module 1. Now you need an API key so your Python code can call Claude programmatically.

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Sign in with the same account you use for claude.ai.
3. Click **Settings** in the left sidebar, then **API Keys**.
4. Click **Create Key**.
5. Give it a name like "DisSysLab" and click **Create**.
6. **Copy the key immediately** — you won't see it again. It looks like `sk-ant-api03-...`.
7. Set it as an environment variable in your terminal:

**macOS / Linux:**
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-your-key-here'
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

To make this permanent, add the export line to your `~/.bashrc` or `~/.zshrc` file.

**Verify it works:**
```python
python3 -c "
from anthropic import Anthropic
client = Anthropic()
msg = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Say hello in 5 words.'}]
)
print(msg.content[0].text)
print('API key works!')
"
```

If you see a greeting followed by "API key works!" — you're ready.

### Upload Component Files to Your Claude Project

In Module 1, your Claude Project had only `CLAUDE_CONTEXT.md`. For Module 2, Claude needs to see the actual source code of the real components so it generates correct imports and constructor parameters.

1. Open your **DisSysLab** project on [claude.ai](https://claude.ai).
2. Go to the project's **Files** section.
3. Upload these files from your DisSysLab repository:
   - `components/sources/bluesky_jetstream_source.py`
   - `components/transformers/claude_agent.py`
   - `components/transformers/prompts.py`
   - `components/sinks/jsonl_recorder.py`

`CLAUDE_CONTEXT.md` should already be there from Module 1. If not, upload it too.

That's the complete setup. You won't need to do this again — these files stay in your project.

---

## Part 2: Describe Your App to Claude (5 minutes)

Open a new conversation inside your DisSysLab project and type:

> Build me an app that monitors BlueSky for posts mentioning AI or machine learning. Use BlueSkyJetstreamSource with max_posts=20. Analyze the sentiment of each post using real Claude AI with the sentiment_analyzer prompt. Then extract the names of people and places mentioned using the entity_extractor prompt. Save the fully enriched results to a JSONL file. Use real components — BlueSkyJetstreamSource, ClaudeAgent, and JSONLRecorder.

Claude generates a complete app. Copy the code into `my_real_app.py` in the DisSysLab root directory and run it:

```bash
python3 my_real_app.py
```

You should see real BlueSky posts flowing through real AI analysis, with results saved to a JSONL file. Open the file and look — each line is a JSON object with the original text, sentiment, score, and extracted names.

**You just built a live AI-powered social media monitoring system.**

---

## Part 3: Side-by-Side with Module 1 (10 minutes)

Put your Module 1 code next to your Module 2 code. Notice:

**What changed:**

| | Module 1 (mock) | Module 2 (real) |
|---|---|---|
| Source | `MockRSSSource(feed_name="hacker_news")` | `BlueSkyJetstreamSource(search_keywords=["AI"], max_posts=20)` |
| AI | `MockClaudeAgent(task="sentiment_analysis")` | `ClaudeAgent(get_prompt("sentiment_analyzer"))` |
| Sink | `Sink(fn=print, ...)` | `Sink(fn=recorder.run, ...)` |

**What didn't change:**

- The transform functions have the same structure — call `.run(text)`, get a dict back, use the dict fields.
- The network definition is the same — `network([(source, transform), ...])`.
- The `run_network()` call is identical.
- Filtering with `None` works the same way.

**The conclusion:** You learned the framework in Module 1. Module 2 didn't teach you new framework concepts — it showed you that the same pattern works with real data and real AI. That's the power of DisSysLab's uniform interface.

---

## Part 4: Understanding the Real Components (15 minutes)

### BlueSkyJetstreamSource

Connects to BlueSky's public Jetstream API — a real-time stream of every post on the platform. The `search_keywords` parameter filters for posts containing your keywords. Each call to `.run()` returns one post as a string. After `max_posts` posts, it returns `None` to stop the network.

```python
bluesky = BlueSkyJetstreamSource(search_keywords=["AI", "machine learning"], max_posts=20)
```

No authentication is needed — the Jetstream API is public. You're reading the same data that anyone on BlueSky can see.

### ClaudeAgent

Takes a prompt string (from the prompt library or custom), sends each piece of text to the Claude API as a message, and parses the JSON response into a Python dict. Same `.run(text)` interface as `MockClaudeAgent`.

```python
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

sentiment_analyzer = ClaudeAgent(get_prompt("sentiment_analyzer"))
result = sentiment_analyzer.run("This new AI model is incredible!")
# result: {"sentiment": "POSITIVE", "score": 0.85, "reasoning": "..."}
```

The prompt defines *what* the AI does. The `get_prompt()` function looks up a pre-built prompt from the library. The agent handles the API call, JSON parsing, error handling, and token tracking.

### JSONLRecorder

Opens a file and appends each result as one JSON line. JSONL (JSON Lines) is a common format for structured log data — each line is a complete, valid JSON object.

```python
recorder = JSONLRecorder(path="output.jsonl", mode="w", flush_every=1, name="archive")
```

After the network runs, you can open `output.jsonl` and see every result:

```json
{"text": "Just tried the new Claude model...", "sentiment": "POSITIVE", "score": 0.82, "people": ["Claude"], "locations": []}
{"text": "AI regulation debate in Congress...", "sentiment": "NEUTRAL", "score": 0.05, "people": [], "locations": ["Congress"]}
```

---

## Part 5: The Prompt Library (10 minutes)

The `sentiment_analyzer` and `entity_extractor` prompts you used are two of 30+ pre-built prompts in the library. Browse them:

```python
from components.transformers.prompts import print_prompt_catalog
print_prompt_catalog()
```

Or search for a specific capability:

```python
from components.transformers.prompts import search_prompts
print(search_prompts("spam").keys())
```

Every prompt follows the same pattern: it tells Claude what to analyze and what JSON format to return. Your transform function receives that JSON as a Python dict and uses it however you want.

**You don't need to understand prompt engineering to use these.** Just call `get_prompt("key")` and pass it to `ClaudeAgent`. The prompts are pre-tested and produce consistent JSON output.

If you're curious about writing your own prompts, Anthropic's prompt engineering documentation is at [docs.anthropic.com](https://docs.anthropic.com). The file `tutorial_prompts_to_python.md` in the DisSysLab repo also walks through the Prompt → JSON → Python pattern in detail.

---

## Part 6: Make It Yours (15 minutes)

### Experiment 1: Change the search keywords

Ask Claude:

> Change my app to monitor BlueSky for posts about climate change instead of AI.

Or change it yourself — it's one line:

```python
bluesky = BlueSkyJetstreamSource(search_keywords=["climate", "climate change"], max_posts=20)
```

### Experiment 2: Swap the AI analysis

Ask Claude:

> Replace sentiment analysis with urgency detection. Use the urgency_detector prompt.

Now your app detects urgent posts instead of emotional ones. Same pipeline, different prompt.

### Experiment 3: Add a filter

Ask Claude:

> Add a filter after sentiment analysis that drops neutral posts. Only save positive and negative posts to the file.

This combines real AI with filtering — the `None` pattern from Module 1 works identically with real data.

### Experiment 4: Add a second transform

Ask Claude:

> Add topic classification after entity extraction. Use the topic_classifier prompt. Include the topic in the saved output.

Your pipeline now runs three AI analyses in sequence: sentiment → entity extraction → topic classification. Each transform enriches the dict, and the sink gets the fully enriched result.

### Experiment 5: Run longer

Change `max_posts=20` to `max_posts=100` or remove the limit entirely for continuous monitoring. Note: each post costs a fraction of a cent in API calls. You can check your spending with:

```python
sentiment_agent.print_usage_stats()
```

### Experiment 6: Describe something completely different

> Build me an app that monitors BlueSky for posts about my university, detects if they're complaints or praise using sentiment analysis, extracts any person names mentioned, and saves only the complaints to a file. Use real components.

Compare what Claude generates with your original app. Same pattern, different application.

---

## Part 7: What You Should See

Your output will differ because BlueSky is live — you're seeing real posts from real people in real time. But the structure looks like this:

```
📡 Monitoring BlueSky for: AI, machine learning (20 posts)

  😊 [POSITIVE] "Just deployed my first ML model to production — it actually works!"
     People: none | Places: none
  😐 [ NEUTRAL] "Anyone have recommendations for machine learning courses?"
     People: none | Places: none
  😊 [POSITIVE] "Yann LeCun's talk at NeurIPS was absolutely fascinating"
     People: Yann LeCun | Places: NeurIPS
  😞 [NEGATIVE] "Frustrated with the AI hype — most of these tools don't deliver"
     People: none | Places: none
  ...

✅ Done! 20 posts processed. Results saved to output.jsonl

Claude API usage:
  API Calls:       40
  Input Tokens:    12,350
  Output Tokens:   3,200
  Estimated Cost:  $0.0851 USD
```

Notice: the sentiment analysis is dramatically better than the keyword-matching mock from Module 1. Real AI understands nuance, sarcasm, context. That's the difference one import swap makes.

---

## Part 8: Exploration

### Test Claude's limits

Try removing the component files from your Claude Project and regenerating the app with only `CLAUDE_CONTEXT.md`. Does Claude still produce correct code? What breaks? What still works? This teaches you something about how AI assistants use context — more specific information produces better results.

### Other sources you could build

BlueSky is just one data source. Any Python code that returns data can be a DisSysLab Source:

- **RSS feeds** — `RSSSource` is already in the component library (no authentication needed)
- **Reddit** — the Reddit API has a free tier
- **Email** — IMAP libraries let you read incoming mail
- **Databases** — query results become source data
- **Files** — CSV, JSON, text files on disk
- **Any API** — if you can call it from Python, you can wrap it

Module 3 shows how to combine multiple sources. And you can always ask Claude to help you build a custom source for any API.

---

## What You've Learned

- **Real components have the same interface as mock components.** The swap is one import line.
- **The Prompt → JSON → Python pattern.** A prompt defines what AI does. JSON structures the output. Your Python function uses the result.
- **The prompt library** has 30+ pre-built prompts ready to use. Browse with `print_prompt_catalog()`.
- **Enrichment pipelines** — each transform adds fields to the data dict. The final result contains everything.
- **Live data is different.** Results vary because the data is real. AI analysis captures nuance that keyword matching misses.

## What's Next

**[Module 3: Multiple Sources, Multiple Destinations](../module_03/)** — pull from BlueSky *and* an RSS feed at the same time, and send results to both a file *and* email alerts. Your app goes from a single pipeline to a real monitoring system.
