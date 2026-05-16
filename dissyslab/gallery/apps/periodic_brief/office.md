# Office: periodic_brief

# A multi-source briefing office. By default everything goes
# straight to the HTML brief sink — no LLM calls, ~10 seconds
# end-to-end. See README's Tier 2 section to enable a sense → think
# → respond news pipeline (entity / topic / urgency tagging plus a
# writer that composes per-article briefs) when you're ready to pay
# the inference cost.

Sources: bbc_world(max_articles=5), npr_news(max_articles=5), weather(city="Pasadena", max_readings=1), stocks(ticker="AAPL", max_readings=1), stocks_2(ticker="NVDA", max_readings=1), stocks_3(ticker="MSFT", max_readings=1)
Sinks: periodic_brief_html_sink(path="brief.html")

Connections:
bbc_world's destination is periodic_brief_html_sink.
npr_news's destination is periodic_brief_html_sink.
weather's destination is periodic_brief_html_sink.
stocks's destination is periodic_brief_html_sink.
stocks_2's destination is periodic_brief_html_sink.
stocks_3's destination is periodic_brief_html_sink.
