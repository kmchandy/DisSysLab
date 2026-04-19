# Office: news_filter

Sources: al_jazeera(max_articles=2), bbc_world(max_articles=2)
Sinks: console_printer, jsonl_recorder(path="filtered_output.jsonl")

Agents:
Felix is a filter.

Connections:
al_jazeera's destination is Felix.
bbc_world's destination is Felix.
Felix's keeper is console_printer.
Felix's discard is jsonl_recorder.