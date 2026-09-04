# Office: caltech_radar

Sources: rss(url="https://www.caltech.edu/campus-life-events/calendar/rss", name="caltech_calendar", max_articles=15), arxiv_cs_ai(max_articles=10), weather(city="Pasadena", max_readings=1)
Sinks: periodic_brief_html_sink(path="radar.html"), jsonl_recorder(path="not_for_me.jsonl")

Agents:
Screen is a cs_ai_filter.

Connections:
rss's destination is Screen.
arxiv_cs_ai's destination is Screen.
Screen's keep is periodic_brief_html_sink.
Screen's discard is jsonl_recorder.
weather's destination is periodic_brief_html_sink.
