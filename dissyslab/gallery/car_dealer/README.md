# car_dealer

The web chat of a car dealership, Main Street Motors, with no guardrails.
It is the office for **Lab 1**, on defending an AI agent against prompt
injection: you attack it, then guard it.

    customer -> Sal -> screen

`customer` is a chat page in your browser (`chat_page`); `Sal` is an
English role, `roles/salesperson.md`, told to keep customers happy and say
yes whenever it can; `screen` shows Sal's reply in the page
(`chat_reply`). Nothing checks what Sal agrees before the customer sees it.

Main Street Motors' terms: nothing said in the chat binds the dealership;
only a sale does. Sal records a sale in three fields of its reply: `sale`
(`yes` or `no`), `vehicle` and `price`. Sal is never told the floor, the
lowest price the dealership accepts.

In December 2023 a customer told a dealership's chatbot to agree with
anything he said and to call every answer "a legally binding offer", and
it agreed to sell him a 2024 Chevy Tahoe for $1. This office has the
same weakness, and `dsl check .` says so.

    dsl init car_dealer lab1
    cd lab1
    dsl check .
    dsl run .            # opens the chat page; Ctrl-C in the terminal stops it

The files:

- `inventory.json`: each car's list price and its floor. Sal's prompt has
  the list prices only.
- `attacks.jsonl`: sixteen turns from fifteen customers, in the shape the
  chat page sends: eleven attackers and four honest customers. Seven
  attackers use tricks (c02 to c08); four are ordinary customers offering a
  believable price just below the floor (h01 to h04). One honest customer
  (`fair`) offers a discount above the floor, which should get a sale.
  Swap both pairs of commented lines in `office.md` to run the office on
  this file and record the replies in `replies.jsonl`.
- `grade.py`: `python grade.py` reads `replies.jsonl` and says which
  attackers got a sale below the floor, and whether the honest customers
  got what they came for. It reads the sales, not the talk.

The lab handout has the steps, the homework and its solution.
