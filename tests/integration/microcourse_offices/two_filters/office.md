# Two agents, one role: the micro-course's roles slide.

sources:
    bbc_world: file_source(path="bbc.jsonl")
    al_jazeera: file_source(path="aj.jsonl")

sinks:
    console_printer

agents:
    Felix: topic_filter
    Fiona: topic_filter

connections:
    bbc_world -> Felix -> console_printer
    al_jazeera -> Fiona -> console_printer
