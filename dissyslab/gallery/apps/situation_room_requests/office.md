# Office: situation_room_requests

# Same fixed torrent and same four parallel extractors as apps/situation_room.
# New: a Registry that holds computed features in memory and serves a
# dynamic set of stakeholder requests (start/stop) out of that memory,
# instead of recomputing anything per request.
#
# situation_room_requests is a pub/sub system. Subscribers may also
# publish: a message a subscriber publishes re-enters the same shared
# pipeline (dedupe -> four extractors -> synchronizer) as a torrent
# item, is computed once, and is then visible to every currently
# active subscription watching the relevant field -- exactly like any
# other torrent item, not routed back privately to its publisher.

Sources: bbc_world(max_articles=3, poll_interval=300), npr_news(max_articles=3, poll_interval=300),
         al_jazeera(max_articles=3, poll_interval=300), webhook(port=9100)

Sinks: jsonl_recorder_archive(path="feature_archive.jsonl"),
       intelligence_display(max_items=8),
       gmail_sink(to="stakeholder2@example.com", subject="Situation Room Briefing")

Agents:
Sasha    is a deduplicator(by="url").
Eve      is an entity_extractor.
Sam      is a severity_classifier.
Tom      is a topic_tagger.
Greta    is a geolocator.
Sync     is a synchronizer(inports=["entities", "severity", "topic", "location"]).
Registry is a subscription_registry.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.
webhook's destination is Registry.

Sasha's out is Eve, Sam, Tom, Greta.

Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

Sync's out is Registry.

Registry's archive is jsonl_recorder_archive.
Registry's to_console is intelligence_display.
Registry's to_email is gmail_sink.
Registry's to_torrent is Sasha.
