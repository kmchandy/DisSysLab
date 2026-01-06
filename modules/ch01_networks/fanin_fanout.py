# modules/ch02_networks/dual_output.py

from dsl import network
from dsl.decorators import msg_map
from dsl.connectors.sink_jsonl_recorder import JSONLRecorder
from .simple_text_analysis import from_social_media


@msg_map(input_keys=["text"], output_keys=["sentiment", "keywords"])
def sentiment_with_keywords(text):
    """Extracts sentiment and key emotional words"""
    positive = ['amazing', 'best', 'promoted', 'great', 'excited', 'love']
    negative = ['terrible', 'stuck', 'worst', 'lost', 'bad']

    text_lower = text.lower()
    found_keywords = []

    for word in positive:
        if word in text_lower:
            found_keywords.append(f"+{word}")
    for word in negative:
        if word in text_lower:
            found_keywords.append(f"-{word}")

    pos_count = sum(1 for kw in found_keywords if kw.startswith('+'))
    neg_count = sum(1 for kw in found_keywords if kw.startswith('-'))

    if pos_count > neg_count:
        sentiment = "POSITIVE"
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    return sentiment, found_keywords


@msg_map(input_keys=["text"], output_keys=["urgency", "metrics"])
def urgency_analyzer(text):
    """Analyzes urgency and calculates text metrics"""
    urgent_indicators = ['!', 'urgent', 'asap', 'immediately', 'critical']

    text_lower = text.lower()
    urgency_score = sum(
        1 for indicator in urgent_indicators if indicator in text_lower)

    if urgency_score >= 2:
        urgency = "HIGH"
    elif urgency_score == 1:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    metrics = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "urgency_score": urgency_score
    }

    return urgency, metrics

# Real-time display (prints to console)


@msg_map(input_keys=["id", "text", "sentiment", "keywords"])
def display_realtime(id, text, sentiment, keywords):
    """Displays sentiment analysis in real-time"""
    kw_str = ", ".join(keywords) if keywords else "none"
    print(f"[REALTIME] Post {id}: [{sentiment}] - Keywords: {kw_str}")
    print(f"           Text: {text[:50]}...")


# Archive to JSONL file (for later analysis)
archive_recorder = JSONLRecorder(
    path="urgency_analysis.jsonl",
    mode="w",
    flush_every=1,
    name="urgency_archive"
)


@msg_map(input_keys=["id", "text", "urgency", "metrics"])
def archive_to_file(id, text, urgency, metrics):
    """Archives urgency analysis to JSONL file"""
    record = {
        "id": id,
        "text": text,
        "urgency": urgency,
        "metrics": metrics
    }
    archive_recorder(record)
    print(f"[ARCHIVE]  Post {id}: [{urgency} urgency] - Archived to file")


"""
Network Structure (Fanout to Different Destinations):

                    +-------------+
                    |  from_posts |
                    +-------------+
                       /       \
                      /         \
                     v           v
         +-------------------+  +------------------+
         |   sentiment_with  |  |    urgency       |
         |     keywords      |  |    analyzer      |
         +-------------------+  +------------------+
                  |                      |
                  v                      v
         +-------------------+  +------------------+
         | display_realtime  |  | archive_to_file  |
         |   (console)       |  |    (JSONL)       |
         +-------------------+  +------------------+
"""

g = network([
    (from_posts, sentiment_with_keywords),
    (from_posts, urgency_analyzer),
    (sentiment_with_keywords, display_realtime),
    (urgency_analyzer, archive_to_file)
])

g.run_network()

# Finalize the file recorder
archive_recorder.finalize()

print("\n=== Dual Output Summary ===")
print("Sentiment analysis displayed in real-time")
print("Urgency analysis archived to: urgency_analysis.jsonl")
print("\nTo view archived data:")
print("  cat urgency_analysis.jsonl | jq '.'")
