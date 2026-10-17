# car_dealer

The web chat of a car dealership, Main Street Motors, with no guardrails.
It is the office for **Lab 1**: you attack it, then guard it.

    customer -> Sal -> screen

`customer` is a chat page in your browser (`chat_page`); `Sal` is an
English role, `roles/salesperson.md`, told to keep customers happy and say
yes whenever it can; `screen` shows Sal's reply in the page
(`chat_reply`). Nothing checks what Sal says before the customer sees it.

In December 2023 a customer told a dealership's chatbot to agree with
anything he said and to call every answer "a legally binding offer", and
it agreed to sell him a 2024 Chevy Tahoe for $1. This office has the
same weakness, and `dsl check .` says so.

    dsl init car_dealer lab1
    cd lab1
    dsl check .
    dsl run .            # opens the chat page; Ctrl-C in the terminal stops it

The files:

- `inventory.json`: each car's list price and its floor, the lowest price
  the dealership will accept. Sal's prompt has the list prices only.
- `attacks.jsonl`: eleven turns of conversation, eight attacks and three
  honest customers, in the shape the chat page sends. Swap the two
  commented lines in `office.md` to run the office on this file and
  record the replies in `replies.jsonl`.
- `grade.py`: `python grade.py` reads `replies.jsonl` and says which
  attacks got through and whether the honest customers were helped.

The lab handout has the steps.
