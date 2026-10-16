# situation_room_pro: news from three feeds, analysed four ways at once,
# joined, and written up as briefings by a stronger model.

sources:
    bbc_world(max_articles=3)
    npr_news(max_articles=3)
    al_jazeera(max_articles=3)

sinks:
    intelligence_display(title="headline", text="summary", color="severity")
    jsonl_recorder(path="briefings.jsonl")

agents:
    Sasha: deduplicator(by="url")
    Eve: entity_extractor
    Sam: severity_classifier
    Tom: topic_tagger
    Greta: geolocator
    Sync: synchronizer(on="url")
    Riley: writer(ai="anthropic")

connections:
    bbc_world, npr_news, al_jazeera -> Sasha -> Eve, Sam, Tom, Greta
    Eve -> Sync.entities
    Sam -> Sync.severity
    Tom -> Sync.topic
    Greta -> Sync.location
    Sync -> Riley -> intelligence_display, jsonl_recorder
