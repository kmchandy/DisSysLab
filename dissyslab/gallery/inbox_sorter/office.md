# inbox_sorter: messages to the course staff, sorted by how soon they need an answer.

sources:
    inbox: file_source(path="messages.jsonl")

sinks:
    console_printer
    urgent: jsonl_recorder(path="urgent.jsonl")
    later: jsonl_recorder(path="later.jsonl")

agents:
    Tri: triage
    Rex: router(on="urgency")

connections:
    inbox -> Tri -> Rex
    Rex.urgent -> urgent, console_printer
    Rex.routine -> later
