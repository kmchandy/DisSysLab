# office: Sal proposes a sale; a Python agent decides whether it is booked.

sources:
    customer: file_source(path="conversations.jsonl")

sinks:
    sales: jsonl_recorder(path="sales.jsonl")
    replies: jsonl_recorder(path="replies.jsonl")
    refusals: jsonl_recorder(path="refused.jsonl")

agents:
    Sal: salesperson
    Guard: floor_guard
    Rex: router(on="book")

connections:
    customer -> Sal -> Guard -> Rex
    Rex.yes -> sales, replies
    Rex.no -> replies
    Sal.refused -> refusals
