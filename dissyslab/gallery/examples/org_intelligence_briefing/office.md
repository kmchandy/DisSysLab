# Office: intelligence_briefing

Sources: al_jazeera(max_articles=5), bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: intelligence_display, jsonl_recorder(path="briefing.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
al_jazeera's destination is Alex.
bbc_world's destination is Alex.
npr_news's destination is Alex.
Alex's editor is Morgan.
Alex's discard is jsonl_recorder.
Morgan's archivist are intelligence_display and jsonl_recorder.
