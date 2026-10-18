sources:
    customer: file_source(path="chats.jsonl")
sinks:
    console_printer
agents:
    Rita: requests
connections:
    customer -> Rita -> console_printer
