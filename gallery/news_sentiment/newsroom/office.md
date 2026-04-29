Sources: al_jazeera(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600),
         npr_news(max_articles=10, poll_interval=600)
Sinks: intelligence_display(max_items=8),
       jsonl_recorder(path="news_feed.jsonl")

Agents:
Riley is an analyst.
Morgan is an editor.

Connections:
al_jazeera's destination is Riley.
bbc_world's destination is Riley.
npr_news's destination is Riley.
Riley's editor is Morgan.
Riley's discard is jsonl_recorder.
Morgan's situation_room are intelligence_display and jsonl_recorder.