# car_dealer: a dealership's chat assistant, with no guardrails (Lab 1).

sources:
    customer: chat_page(title="Main Street Motors")
    # customer: file_source(path="attacks.jsonl")

sinks:
    screen: chat_reply
    # screen: jsonl_recorder(path="replies.jsonl")

agents:
    Sal: salesperson

connections:
    customer -> Sal -> screen
