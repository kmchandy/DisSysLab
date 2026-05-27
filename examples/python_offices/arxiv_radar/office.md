# Office: ticket_router

Sources: webhook(port=8000, path='/tickets')
Sinks: slack_sink_alerts(webhook_url_env='SLACK_ONCALL_WEBHOOK'), jsonl_recorder_archive(path='tickets_archive.jsonl')

Agents:
Sasha is a deduplicator(by='url').
Eve is a severity_classifier.
Sam is an urgency_classifier.
Tom is a category_classifier.
Sync is a synchronizer(inports=["severity_classifier", "urgency_classifier", "category_classifier"]).
Riley is a summary_writer.

Connections:
webhook's destination is Sasha.

Sasha's out is Eve, Sam, Tom.

Eve's out is Sync's severity_classifier.
Sam's out is Sync's urgency_classifier.
Tom's out is Sync's category_classifier.

Sync's out is Riley.
Riley's out is slack_sink_alerts, jsonl_recorder_archive.
