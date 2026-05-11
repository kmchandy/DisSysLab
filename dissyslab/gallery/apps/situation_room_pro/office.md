# Office: situation_room_pro

Sources: bbc_world(max_articles=1), npr_news(max_articles=1), al_jazeera(max_articles=1)
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl"), jsonl_recorder_discard(path="rejected.jsonl")

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer.
Riley is a writer.
Jordan is an evaluator.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.

Sasha's out is Eve, Sam, Tom, Greta.

Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

Sync's out is Riley.
Riley's out is Jordan.
Jordan's publish is intelligence_display, jsonl_recorder_briefing.
Jordan's revise is jsonl_recorder_discard.
