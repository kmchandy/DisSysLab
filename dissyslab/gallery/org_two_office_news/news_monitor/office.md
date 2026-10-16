# news_monitor: keeps the articles on the topic.

inputs:
    articles

outputs:
    kept

sinks:
    discard

agents:
    Felix: topic_filter
    Rex: router(on="on_topic")

connections:
    articles -> Felix -> Rex
    Rex.yes -> kept
    Rex.no -> discard
