# Office: lead_qualifier

Sources: webhook(port=8001, path='/leads')
Sinks: webhook_sink(webhook_url_env='CRM_WEBHOOK_URL')

Agents:
Sasha is a deduplicator(by='url').
Eve is a summarizer.
Sam is a sentiment_classifier.
Tom is an urgency_classifier.
Sync is a synchronizer(inports=["summarizer", "sentiment_classifier", "urgency_classifier"]).
Riley is a summary_writer.

Connections:
webhook's destination is Sasha.

Sasha's out is Eve, Sam, Tom.

Eve's out is Sync's summarizer.
Sam's out is Sync's sentiment_classifier.
Tom's out is Sync's urgency_classifier.

Sync's out is Riley.
Riley's out is webhook_sink.
