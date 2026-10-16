# returns_desk: one refund at a time; small ones approved, large ones escalated.

sources:
    tickets: file_source(path="tickets.jsonl")

sinks:
    jsonl_recorder(path="outcomes.jsonl")
    console_printer

agents:
    Gate: gate
    Clerk: clerk(limit=50)
    Rex: router(on="clerk_decision")
    Manager: manager

connections:
    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, console_printer, Gate.done
    Rex.escalate -> Manager -> jsonl_recorder, console_printer, Gate.done
