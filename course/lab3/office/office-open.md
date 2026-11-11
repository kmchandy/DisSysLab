# office-open: the same office with no guard. Whatever Sal books is booked.

sources:
    customer: file_source(path="conversations.jsonl")

sinks:
    sales: jsonl_recorder(path="sales.jsonl")
    replies: jsonl_recorder(path="replies.jsonl")
    refusals: jsonl_recorder(path="refused.jsonl")

agents:
    Sal: salesperson
    Rex: router(on="book")

connections:
    customer -> Sal -> Rex
    Rex.yes -> sales, replies
    Rex.no -> replies
    Sal.refused -> refusals
