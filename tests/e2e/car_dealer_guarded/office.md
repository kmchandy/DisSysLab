# car_dealer, guarded: a reference solution to Lab 1 (course staff only).
# The tests lay these files over a copy of dissyslab/gallery/car_dealer.

sources:
    customer: chat_page(title="Main Street Motors")

sinks:
    screen: chat_reply

agents:
    Sal: salesperson_quoting
    Guard: price_guard

connections:
    customer -> Sal -> Guard -> screen
