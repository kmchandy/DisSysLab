# Office: inbox_triage

# An instance of the sense → think → respond pattern; see
# docs/PATTERN_sense_think_respond.md.

Sources: gmail(unread_only=True, max_emails=20)
Sinks: slack_sink(webhook_url_env='SLACK_WEBHOOK_URL'), jsonl_recorder_discard(path='inbox_discard.jsonl')

Agents:
Sasha is a deduplicator(by='url').
Eve is an urgency_classifier.
Sam is a sentiment_classifier.
Tom is a summarizer.
Sync is a synchronizer.
Riley is a summary_writer.

Connections:
gmail's destination is Sasha.

Sasha's out is Eve, Sam, Tom.

Eve's out is Sync's urgency_classifier.
Sam's out is Sync's sentiment_classifier.
Tom's out is Sync's summarizer.

Sync's out is Riley.
Riley's publish is slack_sink.
Riley's discard is jsonl_recorder_discard.
