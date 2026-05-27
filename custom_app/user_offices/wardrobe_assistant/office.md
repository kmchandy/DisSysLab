---
description: Calendar + NOAA weather → outfit picks from your wardrobe, digest + Gmail
---

# Office: wardrobe_assistant

Sources: calendar(url="https://calendar.google.com/calendar/ical/theroast08%40gmail.com/private-8ebd88e31a0a74c1e8a81811f61343bf/basic.ics", poll_interval=300, days_ahead=7),
         web_scraper(url="https://forecast.weather.gov/MapClick.php?lat=34.1478&lon=-118.1445", source_name="nws_forecast", article_selector="li.forecast-tombstone", title_selector="p.period-name", link_selector="img.forecast-icon", text_selector="div.tombstone-container", max_articles=14, poll_interval=1800)

Sinks: intelligence_display(max_items=14),
       jsonl_recorder(path="wardrobe_outfits.jsonl"),
       discard,
       gmail_sink(to="theroast08@gmail.com", subject="Your outfit guide — wardrobe + calendar digest")

Agents:
Casey is a calendar_analyst.
Morgan is a forecast_parser.
Jordan is a wardrobe_stylist.
Riley is a summary_compiler.

Connections:
calendar's destination is Casey.
web_scraper's destination is Morgan.
Casey's stylist is Jordan.
Morgan's summary is intelligence_display.
Jordan's compiler is Riley.
Riley's display are intelligence_display and jsonl_recorder.
Riley's email is gmail_sink.
