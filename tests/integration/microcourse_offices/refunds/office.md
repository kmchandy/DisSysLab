sources:
    tickets: file_source(path="tickets.jsonl")
sinks:
    console_printer
agents:
    Clerk: clerk(limit=50)
connections:
    tickets -> Clerk -> console_printer
