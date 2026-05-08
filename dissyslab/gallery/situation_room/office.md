# Office: situation_room

Inputs:
Outputs:

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), al_jazeera(max_articles=5)
Sinks: intelligence_display, discard

Agents:
Sasha is a merger.
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a four_way_merger.
Cole is a clusterer.
Riley is a writer.
Jordan is an evaluator.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.

Sasha's out are Eve, Sam, Tom and Greta.

Eve's done is Sync's in_entity.
Sam's done is Sync's in_severity.
Tom's done is Sync's in_topic.
Greta's done is Sync's in_geo.

Sync's out_ is Cole.
Cole's brief is Riley.

Riley's draft is Jordan.
Jordan's approve is intelligence_display.
Jordan's revise is Riley.
