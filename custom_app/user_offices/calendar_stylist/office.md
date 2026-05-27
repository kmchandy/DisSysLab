# Office: calendar_stylist

Sources: calendar(url="https://calendar.google.com/calendar/ical/theroast08%40gmail.com/private-8ebd88e31a0a74c1e8a81811f61343bf/basic.ics", poll_interval=300, days_ahead=7),
         web_scraper(url="https://forecast.weather.gov/MapClick.php?lat=34.1478&lon=-118.1445", source_name="nws_forecast", article_selector="li.forecast-tombstone", title_selector="p.period-name", link_selector="img.forecast-icon", text_selector="div.tombstone-container", max_articles=14, poll_interval=1800)

Sinks: intelligence_display(max_items=12),
       jsonl_recorder(path="outfit_suggestions.jsonl"),
       discard,
       gmail_sink(to="theroast08@gmail.com", subject="Your outfit guide — calendar digest")

Agents:
Casey is a calendar_analyst.
Morgan is a forecast_parser.
Jordan is a stylist.
Riley is a summary_compiler.

Connections:
calendar's destination is Casey.
web_scraper's destination is Morgan.
Casey's stylist is Jordan.
Morgan's summary is intelligence_display.
Jordan's compiler is Riley.
Riley's display are intelligence_display and jsonl_recorder.
Riley's email is gmail_sink.
