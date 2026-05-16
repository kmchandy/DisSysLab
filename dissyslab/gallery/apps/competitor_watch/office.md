# Office: competitor_watch

# An instance of the sense → think → respond pattern; see
# docs/PATTERN_sense_think_respond.md.

Sources: bbc_tech(max_articles=10), techcrunch(max_articles=10), venturebeat_ai(max_articles=10)
Sinks: markdown_digest(path='competitors.md')

Agents:
Sasha is a deduplicator(by='url').
Eve is an entity_extractor.
Sam is a sentiment_classifier.
Tom is a topic_tagger.
Sync is a synchronizer.
Riley is a summary_writer.

Connections:
bbc_tech's destination is Sasha.
techcrunch's destination is Sasha.
venturebeat_ai's destination is Sasha.

Sasha's out is Eve, Sam, Tom.

Eve's out is Sync's entity_extractor.
Sam's out is Sync's sentiment_classifier.
Tom's out is Sync's topic_tagger.

Sync's out is Riley.
Riley's out is markdown_digest.
