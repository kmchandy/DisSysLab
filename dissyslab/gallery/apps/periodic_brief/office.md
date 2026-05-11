# Office: periodic_brief

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), weather(city="Pasadena", max_readings=1)
Sinks: periodic_brief_sink(path="brief.md")

Connections:
bbc_world's destination is periodic_brief_sink.
npr_news's destination is periodic_brief_sink.
weather's destination is periodic_brief_sink.
