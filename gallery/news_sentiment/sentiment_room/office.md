Sources: bluesky(max_posts=None, lifetime=None),
Sinks: intelligence_display(max_items=8),
       jsonl_recorder(path="sentiment_log.jsonl")

Agents:
Jamie is a social_listener.
Alex is a sentiment_analyst.

Connections:
bluesky's destination is Jamie.
Jamie's sentiment_analyst is Alex.
Jamie's discard is jsonl_recorder.
Alex's pulse_room are intelligence_display and jsonl_recorder.