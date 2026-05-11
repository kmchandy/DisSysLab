# Office: situation_room

Sources: bluesky(max_posts=None, lifetime=None), al_jazeera(max_articles=10, poll_interval=600), bbc_world(max_articles=10, poll_interval=600)
Sinks: intelligence_display(max_items=8), jsonl_recorder_discard(path="discards.jsonl"), jsonl_recorder_briefing(path="briefings.jsonl")

Agents:
Alex is an analyst.
Morgan is an editor.

Connections:
bluesky's destination is Alex.
al_jazeera's destination is Alex.
bbc_world's destination is Alex.
Alex's keep is Morgan.
Alex's discard is jsonl_recorder_discard.
Morgan's briefing are intelligence_display and jsonl_recorder_briefing.
