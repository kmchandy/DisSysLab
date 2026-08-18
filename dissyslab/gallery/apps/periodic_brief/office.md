# Office: periodic_brief

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), weather(city="Pasadena", max_readings=1)
Sinks: periodic_brief_html_sink(path="brief.html")

Connections:
bbc_world's destination is periodic_brief_html_sink.
npr_news's destination is periodic_brief_html_sink.
weather's destination is periodic_brief_html_sink.
