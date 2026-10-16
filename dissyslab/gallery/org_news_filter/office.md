# org_news_filter: articles about a topic go to the screen, the rest are dropped.

sources:
    al_jazeera(max_articles=2)
    bbc_world(max_articles=2)

sinks:
    console_printer
    discard

agents:
    Felix: topic_filter
    Rex: router(on="on_topic")

connections:
    al_jazeera, bbc_world -> Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
