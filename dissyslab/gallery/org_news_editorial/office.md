# Office: news_editorial

Sources: al_jazeera(max_articles=1), bbc_world(max_articles=1)
Sinks: jsonl_recorder(path="editorial_output.jsonl"), console_printer

Agents:
Susan is an editor.
Anna is a writer.

Connections:
al_jazeera's destination is Susan.
bbc_world's destination is Susan.
npr_news's destination is Susan.
Susan's copywriter is Anna.
Susan's archivist are jsonl_recorder and console_printer.
Anna's client is Susan.
