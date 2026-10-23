"""
---
emits: each ticket, with the decision to pay it or refuse it
kind: author
in: ticket_id, amount (number, >= 0), paid (number, >= 0)
out: ticket_id, amount, decision (pay | refuse)
---
A refund is paid only if it is no more than the customer paid. The
contract can say that both are numbers, 0 or more; it cannot compare
them. That needs code.
"""


class RefundGuard:
    def __call__(self, item):
        decision = "pay" if item["amount"] <= item["paid"] else "refuse"
        return [{"ticket_id": item["ticket_id"], "amount": item["amount"],
                 "decision": decision}]
