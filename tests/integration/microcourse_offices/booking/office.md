sources:
    quotes: file_source(path="quotes.jsonl")
sinks:
    book: booking
connections:
    quotes -> book
