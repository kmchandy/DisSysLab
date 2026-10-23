# refund_guard: a refund is paid only if it is no more than the customer paid.

sources:
    tickets: file_source(path="tickets.jsonl")

sinks:
    console_printer

agents:
    Guard: refund_guard

connections:
    tickets -> Guard -> console_printer
