sources:
    articles: file_source(path="articles.jsonl")
sinks:
    console_printer
    discard
agents:
    Felix: topic_filter
    Rex: router(on="on_topic")
connections:
    articles -> Felix -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
