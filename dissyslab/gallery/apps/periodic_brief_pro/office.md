# Office: periodic_brief_pro

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), weather(city="Pasadena", max_readings=1), stocks(ticker="AAPL", max_readings=1), stocks_2(ticker="NVDA", max_readings=1), stocks_3(ticker="MSFT", max_readings=1), calendar(days_ahead=1), gmail(unread_only=True, max_emails=20)
Sinks: periodic_brief_html_sink(path="brief.html"), discard

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Tom is a topic_tagger.
Sam is an urgency_classifier.
Felix is a relevance_filter.
Sync is a synchronizer(inports=["entity_extractor", "topic_tagger", "urgency_classifier"]).
Riley is a summary_writer.
Mail is a mail_summariser.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.

Sasha's out is Eve, Tom, Sam.

Eve's out is Sync's entity_extractor.
Tom's out is Sync's topic_tagger.
Sam's out is Sync's urgency_classifier.

Sync's out is Felix.
Felix's keep is Riley.
Felix's discard is discard.
Riley's out is periodic_brief_html_sink.

gmail's destination is Mail.
Mail's keep is periodic_brief_html_sink.
Mail's discard is discard.

weather's destination is periodic_brief_html_sink.
stocks's destination is periodic_brief_html_sink.
stocks_2's destination is periodic_brief_html_sink.
stocks_3's destination is periodic_brief_html_sink.
calendar's destination is periodic_brief_html_sink.
