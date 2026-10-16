# returns_desk

A desk that finishes one refund before taking the next. The gate admits a
ticket; the clerk approves it if it is small and escalates it otherwise;
the manager decides escalated ones. Both ends of the work tell the gate it
is done.

    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, console_printer, Gate.done
    Rex.escalate -> Manager -> jsonl_recorder, console_printer, Gate.done

Each outcome keeps the whole ticket plus `clerk_decision`, and for
escalated tickets `manager_decision`: two annotators, each adding its own
decision, leave an audit trail.
