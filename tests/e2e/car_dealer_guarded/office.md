# car_dealer, guarded: the reference solution to Lab 1 -- the handout's
# guard with its TODO answered, as the handout's solution shows it.
# The tests lay these files over a copy of dissyslab/gallery/car_dealer.

sources:
    customer: chat_page(title="Main Street Motors")

sinks:
    screen: chat_reply

agents:
    Sal: salesperson
    Guard: price_guard

connections:
    customer -> Sal -> Guard -> screen
